from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Protocol


class MaterialRecord(Protocol):
    id: int
    nombre: str
    unidad_base: str
    activo: bool


class PresentacionRecord(Protocol):
    id: int
    material_id: int
    nombre_presentacion: str
    cantidad_base: Decimal


class MaterialRepository(ABC):
    @abstractmethod
    def get_by_id(self, material_id: int) -> MaterialRecord | None:
        """Retrieve a material by its ID."""
        pass

    @abstractmethod
    def list_active(self) -> list[MaterialRecord]:
        """List all active materials."""
        pass
