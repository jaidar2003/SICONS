from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Material, Presentacion
from app.modules.catalog.interfaces.schemas import PresentacionCreate, PresentacionRead
from app.shared.database.session import get_db

router = APIRouter(prefix="/presentaciones", tags=["presentaciones"])


@router.get("", response_model=list[PresentacionRead])
def listar_presentaciones(
    material_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Presentacion]:
    stmt = select(Presentacion).order_by(Presentacion.material_id, Presentacion.nombre_presentacion)
    if material_id is not None:
        stmt = stmt.where(Presentacion.material_id == material_id)
    return list(db.scalars(stmt))


@router.post("", response_model=PresentacionRead, status_code=status.HTTP_201_CREATED)
def crear_presentacion(payload: PresentacionCreate, db: Session = Depends(get_db)) -> Presentacion:
    material = db.get(Material, payload.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    presentacion = Presentacion(**payload.model_dump())
    db.add(presentacion)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La presentacion ya existe para este material") from exc
    db.refresh(presentacion)
    return presentacion

