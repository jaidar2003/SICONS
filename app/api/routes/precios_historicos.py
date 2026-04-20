from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models import Fuente, Material, PrecioHistorico, Presentacion, Usuario
from app.schemas import PrecioHistoricoCreate, PrecioHistoricoRead, PuntoSeriePrecioRead
from app.services.pricing import calcular_precio_normalizado
from app.services.series import PrecioSerieInput, construir_serie_precios


router = APIRouter(tags=["precios historicos"])


@router.get("/precios-historicos", response_model=list[PrecioHistoricoRead])
def listar_precios_historicos(
    material_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    stmt = select(PrecioHistorico).order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    if material_id is not None:
        stmt = stmt.where(PrecioHistorico.material_id == material_id)
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)
    return list(db.scalars(stmt))


@router.get("/materiales/{material_id}/precios", response_model=list[PrecioHistoricoRead])
def listar_precios_por_material(
    material_id: int,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    if db.get(Material, material_id) is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    stmt = (
        select(PrecioHistorico)
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    )
    return list(db.scalars(stmt))


@router.get("/materiales/{material_id}/serie-precios", response_model=list[PuntoSeriePrecioRead])
def obtener_serie_precios_material(
    material_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    stmt = (
        select(PrecioHistorico)
        .options(joinedload(PrecioHistorico.fuente))
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
    )
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)

    registros = [
        PrecioSerieInput(
            fecha=precio.fecha,
            precio_normalizado=precio.precio_normalizado,
            unidad_base=material.unidad_base,
            fuente=precio.fuente.nombre if precio.fuente else None,
        )
        for precio in db.scalars(stmt)
    ]
    return construir_serie_precios(registros)


@router.post("/precios-historicos", response_model=PrecioHistoricoRead, status_code=status.HTTP_201_CREATED)
def crear_precio_historico(
    payload: PrecioHistoricoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> PrecioHistorico:
    material = db.get(Material, payload.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    precio_normalizado = payload.precio_original
    if payload.presentacion_id is not None:
        presentacion = db.get(Presentacion, payload.presentacion_id)
        if presentacion is None:
            raise HTTPException(status_code=404, detail="Presentacion no encontrada")
        if presentacion.material_id != payload.material_id:
            raise HTTPException(status_code=422, detail="La presentacion no pertenece al material")
        precio_normalizado = calcular_precio_normalizado(payload.precio_original, Decimal(presentacion.cantidad_base))

    if payload.fuente_id is not None and db.get(Fuente, payload.fuente_id) is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    precio = PrecioHistorico(
        **payload.model_dump(),
        precio_normalizado=precio_normalizado,
    )
    db.add(precio)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El precio historico ya existe") from exc
    db.refresh(precio)
    return precio
