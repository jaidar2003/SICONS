import json
from datetime import date
from pathlib import Path

from app.modules.pricing.application.forecast_cache import ForecastCacheKey
from app.modules.pricing.application.forecasting import ProphetRow
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead, ForecastSelectionRead
from app.shared.config.settings import settings


class ForecastMaterialResultProtocol:
    dataset: list
    metricas: ForecastMetricasRead
    forecast: list[ForecastPuntoRead]


def _snapshot_path() -> Path:
    return Path(settings.forecast_snapshot_path)


def _leer_snapshots() -> dict:
    path = _snapshot_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _escribir_snapshots(data: dict) -> None:
    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _serializar_key(cache_key: ForecastCacheKey) -> str:
    return f"{cache_key.material_id}:{cache_key.horizonte_meses}:{cache_key.dataset_signature}"


def _serializar_result(result: ForecastMaterialResultProtocol) -> dict:
    return {
        "dataset": [{"ds": fila.ds.isoformat(), "y": fila.y} for fila in result.dataset],
        "metricas": result.metricas.model_dump(mode="json"),
        "forecast": [punto.model_dump(mode="json") for punto in result.forecast],
        "modelo": getattr(result, "modelo", None),
        "supuesto_regresores": getattr(result, "supuesto_regresores", None),
        "seleccion_modelo": result.seleccion_modelo.model_dump(mode="json") if getattr(result, "seleccion_modelo", None) else None,
    }


def _deserializar_result(data: dict):
    from app.modules.pricing.application.forecast_service import (
        FORECAST_MODEL_NAME,
        FORECAST_REGRESSOR_NOTE,
        ForecastMaterialResult,
    )

    return ForecastMaterialResult(
        dataset=[ProphetRow(ds=date.fromisoformat(fila["ds"]), y=float(fila["y"])) for fila in data["dataset"]],
        metricas=ForecastMetricasRead.model_validate(data["metricas"]),
        forecast=[ForecastPuntoRead.model_validate(punto) for punto in data["forecast"]],
        modelo=data.get("modelo") or FORECAST_MODEL_NAME,
        supuesto_regresores=data.get("supuesto_regresores") or FORECAST_REGRESSOR_NOTE,
        seleccion_modelo=ForecastSelectionRead.model_validate(data["seleccion_modelo"]) if data.get("seleccion_modelo") else None,
    )


def cargar_forecast_snapshot(cache_key: ForecastCacheKey):
    snapshots = _leer_snapshots()
    payload = snapshots.get(_serializar_key(cache_key))
    if payload is None:
        return None
    return _deserializar_result(payload)


def guardar_forecast_snapshot(cache_key: ForecastCacheKey, result: ForecastMaterialResultProtocol) -> None:
    snapshots = _leer_snapshots()
    snapshots[_serializar_key(cache_key)] = _serializar_result(result)
    _escribir_snapshots(snapshots)
