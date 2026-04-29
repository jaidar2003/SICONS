from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Material
from app.modules.catalog.interfaces.schemas import MaterialCreate, MaterialRead
from app.shared.database.session import get_db


router = APIRouter(prefix="/materiales", tags=["materiales"])


@router.get("", response_model=list[MaterialRead])
def listar_materiales(db: Session = Depends(get_db), activos: bool | None = None) -> list[Material]:
    stmt = select(Material).order_by(Material.nombre)
    if activos is not None:
        stmt = stmt.where(Material.activo.is_(activos))
    return list(db.scalars(stmt))


@router.post("", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def crear_material(payload: MaterialCreate, db: Session = Depends(get_db)) -> Material:
    material = Material(**payload.model_dump())
    db.add(material)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El material ya existe") from exc
    db.refresh(material)
    return material

