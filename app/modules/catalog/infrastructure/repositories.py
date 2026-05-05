from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.infrastructure.models import Material


class SQLAlchemyMaterialRepository(MaterialRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, material_id: int) -> Optional[Material]:
        return self.session.get(Material, material_id)

    def list_active(self) -> List[Material]:
        stmt = select(Material).where(Material.activo.is_(True)).order_by(Material.id.asc())
        return list(self.session.scalars(stmt))
