from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.pricing.application import imputation
from app.modules.pricing.domain.exceptions import PriceImputationError


class FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False

    def add(self, value: object) -> None:
        self.added.append(value)

    def commit(self) -> None:
        self.committed = True


def test_calculate_estimated_price_aplica_formula() -> None:
    result = imputation._calculate_estimated_price(
        base_price=Decimal("100.00"),
        base_index=Decimal("200.00"),
        target_index=Decimal("250.00"),
    )

    assert result == Decimal("125.00")


def test_impute_monthly_prices_no_reemplaza_precios_reales_y_marca_estimado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = FakeDb()
    material = SimpleNamespace(id=5)
    fuente_estimada = SimpleNamespace(id=99)
    real_january = SimpleNamespace(
        fecha=date(2026, 1, 15),
        origen_dato="REAL",
        presentacion_id=6,
        fuente_id=10,
        precio_original=Decimal("100.00"),
        precio_normalizado=Decimal("100.0000"),
        moneda="ARS",
        numero_comprobante="0001-00000001",
        observaciones=None,
    )
    real_march = SimpleNamespace(
        fecha=date(2026, 3, 10),
        origen_dato="REAL",
        presentacion_id=6,
        fuente_id=10,
        precio_original=Decimal("120.00"),
        precio_normalizado=Decimal("120.0000"),
        moneda="ARS",
        numero_comprobante="0001-00000002",
        observaciones=None,
    )

    monkeypatch.setattr(imputation, "_load_material", lambda _db, _material_id: material)
    monkeypatch.setattr(imputation, "_load_price_rows", lambda _db, _material_id, _end_date: [real_january, real_march])
    monkeypatch.setattr(
        imputation,
        "_load_index_map",
        lambda _db, _series_id, _end_date: {
            date(2026, 1, 1): Decimal("100"),
            date(2026, 2, 1): Decimal("110"),
            date(2026, 3, 1): Decimal("120"),
        },
    )
    monkeypatch.setattr(imputation, "_get_or_create_estimation_fuente", lambda _db: fuente_estimada)

    result = imputation.impute_monthly_prices(
        db,
        material_id=5,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        index_series_id="IPC_NACIONAL",
        source_name="IPC Nacional",
        metodo_estimacion="IPC_NACIONAL",
    )

    assert result.inserted == 1
    assert result.updated == 0
    assert result.skipped_real_months == 2
    assert result.generated_months == [date(2026, 2, 1)]
    assert db.committed is True
    assert len(db.added) == 1
    estimated = db.added[0]
    assert estimated.fecha == date(2026, 2, 1)
    assert estimated.precio_original == Decimal("110.00")
    assert estimated.precio_normalizado == Decimal("110.0000")
    assert estimated.origen_dato == "ESTIMADO"
    assert estimated.metodo_estimacion == "IPC_NACIONAL"
    assert estimated.numero_comprobante == "ESTIMADO-2026-02-01"


def test_impute_monthly_prices_falla_si_falta_indice_base(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb()
    real_january = SimpleNamespace(
        fecha=date(2026, 1, 15),
        origen_dato="REAL",
        presentacion_id=6,
        fuente_id=10,
        precio_original=Decimal("100.00"),
        precio_normalizado=Decimal("100.0000"),
        moneda="ARS",
    )

    monkeypatch.setattr(imputation, "_load_material", lambda _db, _material_id: SimpleNamespace(id=5))
    monkeypatch.setattr(imputation, "_load_price_rows", lambda _db, _material_id, _end_date: [real_january])
    monkeypatch.setattr(imputation, "_load_index_map", lambda _db, _series_id, _end_date: {date(2026, 2, 1): Decimal("110")})
    monkeypatch.setattr(imputation, "_get_or_create_estimation_fuente", lambda _db: SimpleNamespace(id=99))

    with pytest.raises(PriceImputationError, match="indice base"):
        imputation.impute_monthly_prices(
            db,
            material_id=5,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 1),
            index_series_id="IPC_NACIONAL",
            source_name="IPC Nacional",
            metodo_estimacion="IPC_NACIONAL",
        )


def test_impute_monthly_prices_falla_si_falta_indice_objetivo(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb()
    real_january = SimpleNamespace(
        fecha=date(2026, 1, 15),
        origen_dato="REAL",
        presentacion_id=6,
        fuente_id=10,
        precio_original=Decimal("100.00"),
        precio_normalizado=Decimal("100.0000"),
        moneda="ARS",
    )

    monkeypatch.setattr(imputation, "_load_material", lambda _db, _material_id: SimpleNamespace(id=5))
    monkeypatch.setattr(imputation, "_load_price_rows", lambda _db, _material_id, _end_date: [real_january])
    monkeypatch.setattr(imputation, "_load_index_map", lambda _db, _series_id, _end_date: {date(2026, 1, 1): Decimal("100")})
    monkeypatch.setattr(imputation, "_get_or_create_estimation_fuente", lambda _db: SimpleNamespace(id=99))

    with pytest.raises(PriceImputationError, match="meses: 2026-02-01|indice objetivo"):
        imputation.impute_monthly_prices(
            db,
            material_id=5,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 1),
            index_series_id="IPC_NACIONAL",
            source_name="IPC Nacional",
            metodo_estimacion="IPC_NACIONAL",
        )
