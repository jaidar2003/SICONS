from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.repositories import SQLAlchemyPricingRepository
from app.shared.database.session import get_db


def get_pricing_repository(db: Session = Depends(get_db)) -> PricingRepository:
    return SQLAlchemyPricingRepository(db)
