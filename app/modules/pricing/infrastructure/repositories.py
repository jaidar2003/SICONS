from datetime import date
from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import PrecioHistorico


class SQLAlchemyPricingRepository(PricingRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_historical_prices(self, material_id: int, since: date) -> List[PrecioHistorico]:
        stmt = (
            select(PrecioHistorico)
            .options(joinedload(PrecioHistorico.fuente))
            .where(
                PrecioHistorico.material_id == material_id,
                PrecioHistorico.fecha >= since,
            )
            .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
        )
        return list(self.session.scalars(stmt))
