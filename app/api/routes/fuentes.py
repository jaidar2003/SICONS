from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Fuente
from app.schemas import FuenteCreate, FuenteRead


router = APIRouter(prefix="/fuentes", tags=["fuentes"])


@router.get("", response_model=list[FuenteRead])
def listar_fuentes(db: Session = Depends(get_db)) -> list[Fuente]:
    return list(db.scalars(select(Fuente).order_by(Fuente.nombre)))


@router.post("", response_model=FuenteRead, status_code=status.HTTP_201_CREATED)
def crear_fuente(payload: FuenteCreate, db: Session = Depends(get_db)) -> Fuente:
    fuente = Fuente(**payload.model_dump())
    db.add(fuente)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="La fuente ya existe") from exc
    db.refresh(fuente)
    return fuente
