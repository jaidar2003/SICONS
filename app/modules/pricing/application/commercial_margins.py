from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.pricing.infrastructure.models import CommercialMargin


def listar_margenes_comerciales(db: Session) -> list[CommercialMargin]:
    stmt = select(CommercialMargin).order_by(
        CommercialMargin.activo.desc(),
        CommercialMargin.scope.asc(),
        CommercialMargin.updated_at.desc(),
        CommercialMargin.id.desc(),
    )
    return list(db.scalars(stmt))


def crear_margen_comercial(
    db: Session,
    *,
    scope: str,
    material_id: int | None,
    presentation_id: int | None,
    product_key: str | None,
    margen_ganancia_pct: Decimal,
    activo: bool,
) -> CommercialMargin:
    margin = CommercialMargin(
        scope=scope,
        material_id=material_id,
        presentation_id=presentation_id,
        product_key=product_key,
        margen_ganancia_pct=margen_ganancia_pct,
        activo=activo,
    )
    db.add(margin)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible crear el margen comercial") from exc
    db.refresh(margin)
    return margin


def actualizar_margen_comercial(db: Session, *, margin_id: int, update_data: dict) -> CommercialMargin:
    margin = db.get(CommercialMargin, margin_id)
    if margin is None:
        raise HTTPException(status_code=404, detail="Margen comercial no encontrado")

    for field, value in update_data.items():
        setattr(margin, field, value)

    db.add(margin)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="No fue posible actualizar el margen comercial") from exc
    db.refresh(margin)
    return margin
