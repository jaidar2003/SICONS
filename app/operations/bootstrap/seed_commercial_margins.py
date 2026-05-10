from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.shared.database.session import SessionLocal

DEFAULT_GLOBAL_MARGIN = Decimal("20.00")
DEFAULT_MATERIAL_MARGINS: tuple[tuple[str, Decimal], ...] = (
    ("Cemento Portland", Decimal("25.00")),
    ("Pastina", Decimal("30.00")),
    ("Membrana Megaflex", Decimal("22.00")),
)


@dataclass(slots=True)
class SeedCommercialMarginsResult:
    created: int = 0
    updated: int = 0
    warnings: list[str] = field(default_factory=list)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def _resolve_material(db: Session, material_name: str) -> Material | None:
    material = db.scalar(select(Material).where(Material.nombre == material_name))
    if material is not None:
        return material

    target_key = derive_material_key(material_name)
    for candidate in db.scalars(select(Material)).all():
        if derive_material_key(candidate.nombre) == target_key:
            return candidate
    return None


def _find_margin(
    db: Session,
    *,
    scope: str,
    material_id: int | None = None,
    presentation_id: int | None = None,
    product_key: str | None = None,
) -> CommercialMargin | None:
    stmt = select(CommercialMargin).where(CommercialMargin.scope == scope)
    if material_id is None:
        stmt = stmt.where(CommercialMargin.material_id.is_(None))
    else:
        stmt = stmt.where(CommercialMargin.material_id == material_id)

    if presentation_id is None:
        stmt = stmt.where(CommercialMargin.presentation_id.is_(None))
    else:
        stmt = stmt.where(CommercialMargin.presentation_id == presentation_id)

    if product_key is None:
        stmt = stmt.where(CommercialMargin.product_key.is_(None))
    else:
        stmt = stmt.where(CommercialMargin.product_key == product_key)

    stmt = stmt.where(CommercialMargin.activo.is_(True))
    return db.scalar(stmt.order_by(CommercialMargin.updated_at.desc(), CommercialMargin.id.desc()))


def _upsert_margin(
    db: Session,
    *,
    scope: str,
    margen_ganancia_pct: Decimal,
    material_id: int | None = None,
    presentation_id: int | None = None,
    product_key: str | None = None,
) -> bool:
    existing = _find_margin(
        db,
        scope=scope,
        material_id=material_id,
        presentation_id=presentation_id,
        product_key=product_key,
    )
    if existing is not None:
        existing.margen_ganancia_pct = margen_ganancia_pct
        existing.activo = True
        return False

    db.add(
        CommercialMargin(
            scope=scope,
            material_id=material_id,
            presentation_id=presentation_id,
            product_key=product_key,
            margen_ganancia_pct=margen_ganancia_pct,
            activo=True,
        )
    )
    return True


def seed_commercial_margins(db: Session) -> SeedCommercialMarginsResult:
    result = SeedCommercialMarginsResult()

    if _upsert_margin(db, scope="GLOBAL", margen_ganancia_pct=DEFAULT_GLOBAL_MARGIN):
        result.created += 1
    else:
        result.updated += 1

    for material_name, margin in DEFAULT_MATERIAL_MARGINS:
        material = _resolve_material(db, material_name)
        if material is None:
            result.add_warning(
                f"No se encontro el material '{material_name}' para seedear su margen comercial."
            )
            continue

        if _upsert_margin(
            db,
            scope="MATERIAL",
            material_id=material.id,
            margen_ganancia_pct=margin,
        ):
            result.created += 1
        else:
            result.updated += 1

    db.flush()
    return result


def main() -> None:
    with SessionLocal() as db:
        result = seed_commercial_margins(db)
        db.commit()

    print(f"Margenes creados: {result.created}")
    print(f"Margenes actualizados: {result.updated}")
    if result.warnings:
        print("Advertencias:")
        for warning in result.warnings:
            print(f"- {warning}")


if __name__ == "__main__":
    main()
