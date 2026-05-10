import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

from app.modules.pricing.application.forecast_cache import ForecastCacheKey
from app.modules.pricing.application.forecast_service import ForecastMaterialResult
from app.modules.pricing.application.forecasting import ProphetRow
from app.modules.pricing.infrastructure.forecast_snapshots import (
    cargar_forecast_snapshot,
    guardar_forecast_snapshot,
)
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead


def _forecast_result(valor: str) -> ForecastMaterialResult:
    return ForecastMaterialResult(
        dataset=[ProphetRow(ds=date(2024, 1, 1), y=100.0)],
        metricas=ForecastMetricasRead(
            folds=2,
            mae=Decimal("11.32"),
            mape=Decimal("7.74"),
            efectividad_informal=Decimal("92.26"),
        ),
        forecast=[
            ForecastPuntoRead(
                fecha=date(2024, 2, 1),
                precio_proyectado=Decimal(valor),
                precio_equivalente_25kg=Decimal("2750.00"),
                precio_equivalente_50kg=Decimal("5500.00"),
            )
        ],
    )


def test_guardar_y_cargar_forecast_snapshot(monkeypatch, tmp_path) -> None:
    snapshot_path = tmp_path / "forecast_snapshots.json"
    monkeypatch.setattr("app.modules.pricing.infrastructure.forecast_snapshots.settings.forecast_snapshot_path", str(snapshot_path))

    cache_key = ForecastCacheKey(material_id=1, horizonte_meses=3, dataset_signature="firma-1")
    result = replace(
        _forecast_result("110.00"),
        seleccion_modelo=ForecastSelectionRead(
            material_key="cemento-portland",
            modelo_resuelto="prophet_ipim_nivel_general",
            regresores_resueltos=["ipim_nivel_general"],
            mape_referencia=Decimal("4.98"),
            mae_referencia=Decimal("6.76"),
            folds=9,
            confiabilidad="alta",
            origen_decision="material_horizonte",
            justificacion="Configuracion recomendada.",
            no_calibrado=False,
        ),
    )
    guardar_forecast_snapshot(cache_key, result)

    cargado = cargar_forecast_snapshot(cache_key)

    assert cargado is not None
    assert cargado.metricas.mape == Decimal("7.74")
    assert cargado.forecast[0].precio_proyectado == Decimal("110.00")
    assert cargado.seleccion_modelo is not None
    assert cargado.seleccion_modelo.material_key == "cemento-portland"
    assert snapshot_path.exists()


def test_guardar_snapshot_preserva_formato_json(monkeypatch, tmp_path) -> None:
    snapshot_path = tmp_path / "forecast_snapshots.json"
    monkeypatch.setattr("app.modules.pricing.infrastructure.forecast_snapshots.settings.forecast_snapshot_path", str(snapshot_path))

    cache_key = ForecastCacheKey(material_id=2, horizonte_meses=6, dataset_signature="firma-2")
    guardar_forecast_snapshot(cache_key, _forecast_result("125.00"))

    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert "2:6:firma-2" in data
    assert data["2:6:firma-2"]["forecast"][0]["precio_proyectado"] == "125.00"
