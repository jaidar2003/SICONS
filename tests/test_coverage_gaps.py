from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.modules.pricing.application import external_indices, historical_prices
from app.modules.pricing.application import imputation
from app.modules.pricing.application.forecast_service import (
    FORECAST_MODEL_NAME,
    _forecast_material,
    backtesting_forecast,
    forecast_material,
    limpiar_forecast_cache,
    precomputar_forecasts_materiales,
    pronosticar_futuro,
    serie_mensual_material,
)
from app.modules.pricing.application.forecasting import ProphetRow
from app.modules.pricing.domain.exceptions import ExternalIndexSyncError, InsufficientDataException
from app.modules.pricing.domain.exceptions import PriceImputationError
from app.modules.pricing.infrastructure import regressors
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead


class FakeScalarDb:
    def __init__(self, values=None) -> None:
        self.values = list(values or [])
        self.added = []
        self.committed = False

    def scalar(self, _stmt):
        return self.values.pop(0) if self.values else None

    def scalars(self, _stmt):
        return iter(self.values)

    def add(self, value) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.committed = True


def test_sync_external_index_inserta_actualiza_y_deja_igual(monkeypatch: pytest.MonkeyPatch) -> None:
    unchanged = SimpleNamespace(source_name="IPC", value=Decimal("100.0"))
    changed = SimpleNamespace(source_name="Viejo", value=Decimal("90.0"))
    db = FakeScalarDb(values=[None, unchanged, changed])
    monkeypatch.setattr(
        external_indices,
        "fetch_series",
        lambda *_args, **_kwargs: [
            SimpleNamespace(date=date(2026, 1, 1), value=Decimal("100.0")),
            SimpleNamespace(date=date(2026, 2, 1), value=Decimal("100.0")),
            SimpleNamespace(date=date(2026, 3, 1), value=Decimal("110.0")),
        ],
    )

    result = external_indices.sync_external_index(db, series_id="IPC", source_name="IPC")

    assert result.inserted == 1
    assert result.unchanged == 1
    assert result.updated == 1
    assert changed.source_name == "IPC"
    assert changed.value == Decimal("110.0")
    assert db.committed is True


def test_sync_external_index_envuelve_error_cliente(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        external_indices,
        "fetch_series",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(external_indices.DatosArgentinaClientError("fallo")),
    )

    with pytest.raises(ExternalIndexSyncError, match="fallo"):
        external_indices.sync_external_index(FakeScalarDb(), series_id="IPC", source_name="IPC")


def test_list_external_indices_devuelve_scalars() -> None:
    rows = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    assert external_indices.list_external_indices(FakeScalarDb(values=rows), series_id="IPC", source_name="IPC") == rows


def test_historical_prices_rango_limita_fechas_futuras(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 5, 12)

    class FakeResult:
        def one(self):
            return date(2026, 1, 1), date(2099, 1, 1)

    class FakeDb:
        def execute(self, _stmt):
            return FakeResult()

    monkeypatch.setattr(historical_prices, "date", FixedDate)

    result = historical_prices.obtener_rango_precios_historicos(FakeDb())

    assert result["desde"] == date(2026, 1, 1)
    assert result["hasta"] == date(2026, 5, 12)
    assert result["tiene_fechas_futuras"] is True


def test_crear_precio_historico_cubre_errores_basicos() -> None:
    class FakeDb:
        def __init__(self, *, material=None, presentacion=None, fuente=None, fail_commit=False) -> None:
            self.material = material
            self.presentacion = presentacion
            self.fuente = fuente
            self.fail_commit = fail_commit
            self.rolled_back = False

        def get(self, model, _id):
            if model.__name__ == "Material":
                return self.material
            if model.__name__ == "Presentacion":
                return self.presentacion
            if model.__name__ == "Fuente":
                return self.fuente
            return None

        def add(self, _value):
            return None

        def flush(self):
            return None

        def commit(self):
            if self.fail_commit:
                raise IntegrityError("stmt", "params", Exception("duplicado"))

        def rollback(self):
            self.rolled_back = True

        def refresh(self, _value):
            return None

    kwargs = dict(
        material_id=1,
        presentacion_id=None,
        fuente_id=None,
        fecha=date(2026, 1, 1),
        precio_original=Decimal("10.00"),
        moneda="ARS",
        numero_comprobante=None,
        origen_dato="REAL",
        metodo_estimacion=None,
        observaciones=None,
    )

    with pytest.raises(HTTPException) as missing_material:
        historical_prices.crear_precio_historico(FakeDb(), **kwargs)
    assert missing_material.value.status_code == 404

    with pytest.raises(HTTPException) as missing_presentation:
        historical_prices.crear_precio_historico(
            FakeDb(material=SimpleNamespace(id=1)),
            **{**kwargs, "presentacion_id": 10},
        )
    assert missing_presentation.value.detail == "Presentacion no encontrada"

    with pytest.raises(HTTPException) as missing_source:
        historical_prices.crear_precio_historico(
            FakeDb(material=SimpleNamespace(id=1)),
            **{**kwargs, "fuente_id": 99},
        )
    assert missing_source.value.detail == "Fuente no encontrada"

    db = FakeDb(material=SimpleNamespace(id=1), fail_commit=True)
    with pytest.raises(HTTPException) as duplicated:
        historical_prices.crear_precio_historico(db, **kwargs)
    assert duplicated.value.status_code == 409
    assert db.rolled_back is True


def test_listar_precios_historicos_aplica_filtros() -> None:
    rows = [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    class FakeDb:
        def scalars(self, _stmt):
            return iter(rows)

    assert historical_prices.listar_precios_historicos(
        FakeDb(),
        material_id=1,
        desde=date(2026, 1, 1),
        hasta=date(2026, 2, 1),
    ) == rows


def test_imputation_helpers_y_errores_basicos() -> None:
    assert imputation._next_month(date(2026, 12, 1)) == date(2027, 1, 1)
    assert imputation._generate_months(date(2026, 1, 15), date(2026, 3, 2)) == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
    ]

    with pytest.raises(PriceImputationError, match="indice base"):
        imputation._calculate_estimated_price(
            base_price=Decimal("100"),
            base_index=Decimal("0"),
            target_index=Decimal("120"),
        )

    with pytest.raises(PriceImputationError, match="indice objetivo"):
        imputation._calculate_estimated_price(
            base_price=Decimal("100"),
            base_index=Decimal("100"),
            target_index=Decimal("0"),
        )


def test_imputation_carga_entidades_y_fuente(monkeypatch: pytest.MonkeyPatch) -> None:
    existing = SimpleNamespace(id=1)

    class FakeDb:
        def __init__(self, scalar_value=None, material=None, rows=None) -> None:
            self.scalar_value = scalar_value
            self.material = material
            self.rows = rows or []
            self.added = []
            self.flushed = False

        def scalar(self, _stmt):
            return self.scalar_value

        def get(self, _model, _id):
            return self.material

        def scalars(self, _stmt):
            return iter(self.rows)

        def add(self, value):
            self.added.append(value)

        def flush(self):
            self.flushed = True

    assert imputation._get_or_create_estimation_fuente(FakeDb(scalar_value=existing)) is existing

    db = FakeDb()
    created = imputation._get_or_create_estimation_fuente(db)
    assert created.nombre == "Estimado"
    assert db.added == [created]
    assert db.flushed is True

    with pytest.raises(PriceImputationError, match="No existe el material"):
        imputation._load_material(FakeDb(), 99)

    material = SimpleNamespace(id=5)
    assert imputation._load_material(FakeDb(material=material), 5) is material
    assert imputation._load_price_rows(FakeDb(rows=[SimpleNamespace(id=1)]), 5, date(2026, 1, 1))[0].id == 1
    assert imputation._load_index_map(
        FakeDb(rows=[SimpleNamespace(date=date(2026, 1, 15), value=Decimal("123.45"))]),
        "IPC",
        date(2026, 2, 1),
    ) == {date(2026, 1, 1): Decimal("123.45")}


def test_impute_monthly_prices_actualiza_estimado_existente(monkeypatch: pytest.MonkeyPatch) -> None:
    db = SimpleNamespace(committed=False, commit=lambda: setattr(db, "committed", True))
    real = SimpleNamespace(
        fecha=date(2026, 1, 10),
        origen_dato="REAL",
        presentacion_id=7,
        fuente_id=10,
        precio_original=Decimal("100.00"),
        precio_normalizado=Decimal("100.0000"),
        moneda="ARS",
    )
    estimated = SimpleNamespace(
        fecha=date(2026, 2, 1),
        origen_dato="ESTIMADO",
        presentacion_id=None,
        fuente_id=None,
        precio_original=Decimal("0"),
        precio_normalizado=Decimal("0"),
        moneda="ARS",
        numero_comprobante=None,
        metodo_estimacion=None,
        observaciones=None,
    )

    monkeypatch.setattr(imputation, "_load_material", lambda *_args: SimpleNamespace(id=5))
    monkeypatch.setattr(imputation, "_load_price_rows", lambda *_args: [real, estimated])
    monkeypatch.setattr(
        imputation,
        "_load_index_map",
        lambda *_args: {date(2026, 1, 1): Decimal("100"), date(2026, 2, 1): Decimal("125")},
    )
    monkeypatch.setattr(imputation, "_get_or_create_estimation_fuente", lambda *_args: SimpleNamespace(id=99))

    result = imputation.impute_monthly_prices(
        db,
        material_id=5,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 1),
        index_series_id="IPC",
        source_name="IPC",
        metodo_estimacion="IPC",
    )

    assert result.updated == 1
    assert result.inserted == 0
    assert estimated.precio_original == Decimal("125.00")
    assert estimated.precio_normalizado == Decimal("125.0000")
    assert estimated.fuente_id == 99
    assert db.committed is True


def test_impute_monthly_prices_cubre_errores_de_base(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(PriceImputationError, match="start_date"):
        imputation.impute_monthly_prices(
            object(),
            material_id=1,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
            index_series_id="IPC",
            source_name="IPC",
            metodo_estimacion="IPC",
        )

    monkeypatch.setattr(imputation, "_load_material", lambda *_args: SimpleNamespace(id=5))
    monkeypatch.setattr(imputation, "_load_price_rows", lambda *_args: [])
    with pytest.raises(PriceImputationError, match="No hay precios historicos"):
        imputation.impute_monthly_prices(
            object(),
            material_id=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            index_series_id="IPC",
            source_name="IPC",
            metodo_estimacion="IPC",
        )

    estimated_only = SimpleNamespace(fecha=date(2026, 1, 1), origen_dato="ESTIMADO")
    monkeypatch.setattr(imputation, "_load_price_rows", lambda *_args: [estimated_only])
    monkeypatch.setattr(imputation, "_load_index_map", lambda *_args: {date(2026, 1, 1): Decimal("100")})
    monkeypatch.setattr(imputation, "_get_or_create_estimation_fuente", lambda *_args: SimpleNamespace(id=99))
    with pytest.raises(PriceImputationError, match="precio real previo"):
        imputation.impute_monthly_prices(
            object(),
            material_id=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            index_series_id="IPC",
            source_name="IPC",
            metodo_estimacion="IPC",
        )

    future_real = SimpleNamespace(fecha=date(2026, 2, 10), origen_dato="REAL")
    monkeypatch.setattr(imputation, "_load_price_rows", lambda *_args: [future_real])
    monkeypatch.setattr(
        imputation,
        "_load_index_map",
        lambda *_args: {date(2026, 1, 1): Decimal("100")},
    )
    with pytest.raises(PriceImputationError, match="precio real anterior"):
        imputation.impute_monthly_prices(
            object(),
            material_id=5,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            index_series_id="IPC",
            source_name="IPC",
            metodo_estimacion="IPC",
        )


def test_regressors_cargan_csv_y_proyectan(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    dolar = tmp_path / "dolar.csv"
    ipc = tmp_path / "ipc.csv"
    dolar.write_text("fecha,venta\n2026-01-01,100\n2026-01-20,120\n", encoding="utf-8")
    ipc.write_text("fecha,ipc\n2026-01-01,200\n2026-02-01,220\n", encoding="utf-8")

    monkeypatch.setattr(regressors, "OFICIAL_CSV", dolar)
    monkeypatch.setattr(regressors, "IPC_CSV", ipc)

    df = regressors.cargar_regresores_mensuales(pd, ("dolar_oficial", "ipc"))
    assert list(df.columns) == ["ds", "dolar_oficial", "ipc"]
    assert df.loc[0, "dolar_oficial"] == 110

    future = regressors.proyectar_regresores_futuros(
        pd,
        pd.DataFrame({"ds": pd.to_datetime(["2026-01-01", "2026-02-01"]), "ipc": [100.0, 121.0]}),
        [date(2026, 3, 1), date(2026, 4, 1)],
        ("ipc",),
    )
    assert [round(value, 2) for value in future["ipc"].tolist()] == [146.41, 177.16]


def test_regressors_cubren_errores(monkeypatch: pytest.MonkeyPatch) -> None:
    assert regressors.cargar_regresores_mensuales(pd, ()) is None

    with pytest.raises(HTTPException, match="Regresores no soportados"):
        regressors.cargar_regresores_mensuales(pd, ("nope",))

    monkeypatch.setattr(regressors, "IPC_CSV", regressors.PROJECT_ROOT / "no-existe.csv")
    with pytest.raises(HTTPException, match="No se encontro el CSV"):
        regressors.cargar_regresores_mensuales(pd, ("ipc",))

    with pytest.raises(HTTPException, match="No hay historial suficiente"):
        regressors.proyectar_regresores_futuros(pd, pd.DataFrame({"ds": []}), [date(2026, 1, 1)], ("ipc",))

    with pytest.raises(HTTPException, match="No hay datos del regresor"):
        regressors.proyectar_regresores_futuros(
            pd,
            pd.DataFrame({"ds": pd.to_datetime(["2026-01-01"]), "ipc": [None]}),
            [date(2026, 2, 1)],
            ("ipc",),
        )


def test_forecast_material_cubre_insuficiente_y_snapshot_persistido(monkeypatch: pytest.MonkeyPatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    short_dataset = [ProphetRow(ds=date(2026, 1, 1), y=100.0)]
    monkeypatch.setattr("app.modules.pricing.application.forecast_service.serie_mensual_material", lambda *_args: ["serie"])
    monkeypatch.setattr("app.modules.pricing.application.forecast_service.construir_dataset_prophet", lambda *_args, **_kwargs: short_dataset)

    with pytest.raises(InsufficientDataException):
        forecast_material(material, 3, object())

    full_dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0 + index) for index in range(30)]
    persisted = SimpleNamespace(
        dataset=full_dataset,
        metricas=ForecastMetricasRead(folds=1, mae=Decimal("1"), mape=Decimal("2"), efectividad_informal=Decimal("98")),
        forecast=[ForecastPuntoRead(fecha=date(2026, 1, 1), precio_proyectado=Decimal("200"))],
        modelo=FORECAST_MODEL_NAME,
        supuesto_regresores="persistido",
        seleccion_modelo=None,
    )
    monkeypatch.setattr("app.modules.pricing.application.forecast_service.construir_dataset_prophet", lambda *_args, **_kwargs: full_dataset)
    monkeypatch.setattr("app.modules.pricing.application.forecast_service.cargar_forecast_snapshot", lambda _key: persisted)

    result = forecast_material(material, 3, object(), usar_selector_modelo=False)

    assert result.forecast[0].precio_proyectado == Decimal("200")
    assert result.supuesto_regresores == "persistido"


def test_serie_mensual_y_precomputar_forecasts(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDate(date):
        @classmethod
        def today(cls) -> date:
            return date(2026, 5, 15)

    material = SimpleNamespace(id=7, nombre="Arena", unidad_base="kg")
    price = SimpleNamespace(
        fecha=date(2026, 1, 10),
        precio_normalizado=Decimal("100"),
        fuente=SimpleNamespace(nombre="Factura"),
        numero_comprobante="A-1",
    )
    future_price = SimpleNamespace(
        fecha=date(2026, 11, 26),
        precio_normalizado=Decimal("999"),
        fuente=SimpleNamespace(nombre="Factura"),
        numero_comprobante="A-2",
    )
    monkeypatch.setattr("app.modules.pricing.application.forecast_service.date", FixedDate)

    serie = serie_mensual_material(material, SimpleNamespace(get_historical_prices=lambda *_args: [price, future_price]))

    assert len(serie) == 1
    assert serie[0].precio_promedio_normalizado == Decimal("100.0000")

    calls = []
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.forecast_material",
        lambda material, horizonte, _pricing_repo: calls.append((material.id, horizonte)),
    )

    completed = precomputar_forecasts_materiales(
        SimpleNamespace(list_active=lambda: [SimpleNamespace(id=1), SimpleNamespace(id=2)]),
        object(),
        horizontes=(3, 6),
    )

    assert completed == [(1, 3), (1, 6), (2, 3), (2, 6)]
    assert calls == completed


def test_forecast_helpers_sin_regresores() -> None:
    class FakeProphet:
        def __init__(self, **_kwargs):
            self.history = None

        def fit(self, df):
            self.history = df

        def make_future_dataframe(self, periods: int, freq: str):
            assert freq == "MS"
            start = self.history["ds"].max() + pd.DateOffset(months=1)
            return pd.DataFrame({"ds": pd.date_range(start=start, periods=periods, freq=freq)})

        def predict(self, df):
            return pd.DataFrame({
                "ds": df["ds"],
                "yhat": [110.0 + index for index in range(len(df))],
                "yhat_lower": [105.0 + index for index in range(len(df))],
                "yhat_upper": [115.0 + index for index in range(len(df))]
            })
    dataset = [ProphetRow(ds=date(2024, month, 1), y=100.0 + month) for month in range(1, 7)]
    with pytest.MonkeyPatch.context() as monkeypatch_folds:
        monkeypatch_folds.setattr(
            "app.modules.pricing.application.forecast_service.construir_folds_temporales",
            lambda *_args, **_kwargs: [SimpleNamespace(train=dataset[:3], test=dataset[3:5])],
        )
        metrics = backtesting_forecast(pd, FakeProphet, dataset, None, 2, ())
        assert metrics.folds == 1

        puntos = pronosticar_futuro(pd, FakeProphet, dataset, None, (), 2, "kg", "Cemento Portland")
        assert puntos[0].precio_equivalente_25kg is not None

        result = _forecast_material(
            SimpleNamespace(nombre="Arena", unidad_base="kg"),
            2,
            dataset,
            pd,
            FakeProphet,
            SimpleNamespace(
                modelo="prophet_base",
                regresores=(),
                regresores_df=None,
                supuesto_regresores="base",
                seleccion_modelo=None,
            ),
        )
        assert result.modelo == "prophet_base"
