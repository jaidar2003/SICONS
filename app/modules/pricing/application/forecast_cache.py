from dataclasses import dataclass


@dataclass(frozen=True)
class ForecastCacheKey:
    material_id: int
    horizonte_meses: int
    dataset_signature: str


@dataclass
class ForecastCacheEntry:
    result: object
    expires_at: float
