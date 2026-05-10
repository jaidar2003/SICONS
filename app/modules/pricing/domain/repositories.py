from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Protocol


class FuenteRecord(Protocol):
    nombre: str


class PrecioHistoricoRecord(Protocol):
    id: int
    material_id: int
    presentacion_id: int | None
    fecha: date
    precio_original: Decimal
    precio_normalizado: Decimal
    fuente: FuenteRecord | None
    numero_comprobante: str | None


class PricingRepository(ABC):
    @abstractmethod
    def get_historical_prices(self, material_id: int, since: date) -> list[PrecioHistoricoRecord]:
        """Retrieve historical prices for a material since a specific date."""
        pass
