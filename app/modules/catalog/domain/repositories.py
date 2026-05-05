from abc import ABC, abstractmethod
from typing import Optional, List

from app.modules.catalog.infrastructure.models import Material


class MaterialRepository(ABC):
    @abstractmethod
    def get_by_id(self, material_id: int) -> Optional[Material]:
        """Retrieve a material by its ID."""
        pass

    @abstractmethod
    def list_active(self) -> List[Material]:
        """List all active materials."""
        pass
