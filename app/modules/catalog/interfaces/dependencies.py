from fastapi import Depends
from sqlalchemy.orm import Session

from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.infrastructure.repositories import SQLAlchemyMaterialRepository
from app.shared.database.session import get_db


def get_material_repository(db: Session = Depends(get_db)) -> MaterialRepository:
    return SQLAlchemyMaterialRepository(db)
