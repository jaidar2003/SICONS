from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import PrecioHistorico


def obtener_rango_precios_historicos(db: Session) -> dict:
    hoy = date.today()
    desde, hasta_real = db.execute(
        select(func.min(PrecioHistorico.fecha), func.max(PrecioHistorico.fecha))
    ).one()
    hasta = min(hasta_real, hoy) if hasta_real is not None else None
    return {
        "desde": desde,
        "hasta": hasta,
        "hoy": hoy,
        "tiene_fechas_futuras": hasta_real is not None and hasta_real > hoy,
        "hasta_real": hasta_real,
    }


def listar_precios_historicos(
    db: Session,
    *,
    material_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[PrecioHistorico]:
    stmt = select(PrecioHistorico).order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    if material_id is not None:
        stmt = stmt.where(PrecioHistorico.material_id == material_id)
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)
    return list(db.scalars(stmt))


def crear_precio_historico(
    db: Session,
    *,
    material_id: int,
    presentacion_id: int | None,
    fuente_id: int | None,
    fecha: date,
    precio_original: Decimal,
    moneda: str,
    numero_comprobante: str | None,
    origen_dato: str,
    metodo_estimacion: str | None,
    observaciones: str | None,
) -> PrecioHistorico:
    if fecha > date.today():
        raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    precio_normalizado = precio_original
    if presentacion_id is not None:
        presentacion = db.get(Presentacion, presentacion_id)
        if presentacion is None:
            raise HTTPException(status_code=404, detail="Presentacion no encontrada")
        if presentacion.material_id != material_id:
            raise HTTPException(status_code=422, detail="La presentacion no pertenece al material")
        precio_normalizado = calcular_precio_normalizado(precio_original, Decimal(presentacion.cantidad_base))

    if fuente_id is not None and db.get(Fuente, fuente_id) is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    precio = PrecioHistorico(
        material_id=material_id,
        presentacion_id=presentacion_id,
        fuente_id=fuente_id,
        fecha=fecha,
        precio_original=precio_original,
        precio_normalizado=precio_normalizado,
        moneda=moneda,
        numero_comprobante=numero_comprobante,
        origen_dato=origen_dato,
        metodo_estimacion=metodo_estimacion,
        observaciones=observaciones,
    )
    db.add(precio)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El precio historico ya existe") from exc
    db.refresh(precio)
    return precio
