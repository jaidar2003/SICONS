from abc import ABC, abstractmethod
from datetime import date
from typing import List

from app.modules.pricing.infrastructure.models import PrecioHistorico


class PricingRepository(ABC):
    @abstractmethod
    def get_historical_prices(self, material_id: int, since: date) -> List[PrecioHistorico]:
        """Retrieve historical prices for a material since a specific date."""
        pass
