from datetime import date
from types import SimpleNamespace
from decimal import Decimal

from app.modules.pricing.application.forecast_service import (
    ForecastMaterialResult,
    construir_firma_dataset,
    forecast_material,
    limpiar_forecast_cache,
)
from app.modules.pricing.application.forecasting import ProphetRow
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead


def _forecast_result(valor: str) -> ForecastMaterialResult:
    return ForecastMaterialResult(
        dataset=[ProphetRow(ds=date(2024, 1, 1), y=float(valor))],
        metricas=ForecastMetricasRead(
            folds=1,
            mae=Decimal("1.00"),
            mape=Decimal("2.00"),
            efectividad_informal=Decimal("98.00"),
        ),
        forecast=[
            ForecastPuntoRead(
                fecha=date(2024, 2, 1),
                precio_proyectado=Decimal(valor),
                precio_equivalente_25kg=Decimal("2500.00"),
                precio_equivalente_50kg=Decimal("5000.00"),
            )
        ],
    )


def test_construir_firma_dataset_cambia_si_cambia_la_serie() -> None:
    firma_a = construir_firma_dataset([ProphetRow(ds=date(2024, 1, 1), y=100.0)])
    firma_b = construir_firma_dataset([ProphetRow(ds=date(2024, 1, 1), y=101.0)])
    assert firma_a != firma_b


def test_forecast_material_reutiliza_cache_para_la_misma_serie(monkeypatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    dataset = [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30
    llamadas = {"cantidad": 0}

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda material, db: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.construir_dataset_prophet",
        lambda puntos, objetivo: dataset,
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )

    def fake_forecast(material, horizonte_meses, dataset, pd, prophet):
        llamadas["cantidad"] += 1
        return _forecast_result("110.00")

    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    primer = forecast_material(material, 3, object())
    segundo = forecast_material(material, 3, object())

    assert llamadas["cantidad"] == 1
    assert primer.forecast[0].precio_proyectado == Decimal("110.00")
    assert segundo.forecast[0].precio_proyectado == Decimal("110.00")


def test_forecast_material_invalida_cache_si_cambia_el_dataset(monkeypatch) -> None:
    limpiar_forecast_cache()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    datasets = [
        [ProphetRow(ds=date(2024, 1, 1), y=100.0)] * 30,
        [ProphetRow(ds=date(2024, 1, 1), y=101.0)] * 30,
    ]
    resultados = iter([_forecast_result("110.00"), _forecast_result("115.00")])
    llamadas = {"cantidad": 0}

    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.serie_mensual_material",
        lambda material, db: ["serie"],
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.importar_dependencias_forecast",
        lambda: (object(), object(), object(), object(), object()),
    )
    monkeypatch.setattr(
        "app.modules.pricing.application.forecast_service.configurar_cmdstan",
        lambda *args: None,
    )

    def fake_dataset(puntos, objetivo):
        return datasets.pop(0)

    def fake_forecast(material, horizonte_meses, dataset, pd, prophet):
        llamadas["cantidad"] += 1
        return next(resultados)

    monkeypatch.setattr("app.modules.pricing.application.forecast_service.construir_dataset_prophet", fake_dataset)
    monkeypatch.setattr("app.modules.pricing.application.forecast_service._forecast_material", fake_forecast)

    primer = forecast_material(material, 3, object())
    segundo = forecast_material(material, 3, object())

    assert llamadas["cantidad"] == 2
    assert primer.forecast[0].precio_proyectado == Decimal("110.00")
    assert segundo.forecast[0].precio_proyectado == Decimal("115.00")
