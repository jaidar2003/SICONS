from datetime import date
from decimal import Decimal
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.shared.database.session import SessionLocal

FACTURAS_CEMENTO_25KG = [
    ("0256-00044369", date(2025, 7, 29), Decimal("5045.59")),
    ("0256-00044800", date(2025, 8, 18), Decimal("5045.59")),
    ("0256-00045034", date(2025, 8, 28), Decimal("5045.59")),
    ("0256-00045232", date(2025, 9, 5), Decimal("5203.52")),
    ("0256-00045694", date(2025, 9, 29), Decimal("5203.52")),
    ("0256-00046361", date(2025, 10, 31), Decimal("5622.65")),
    ("0256-00046835", date(2025, 11, 26), Decimal("5849.29")),
    ("0256-00047615", date(2025, 12, 26), Decimal("6079.13")),
    ("0256-00048074", date(2026, 1, 29), Decimal("6317.94")),
    ("0280-00171247", date(2026, 2, 28), Decimal("6526.82")),
    ("0256-00048650", date(2026, 3, 3), Decimal("6526.82")),
    ("0256-00049133", date(2026, 3, 25), Decimal("6809.95")),
]


T = TypeVar("T")


def require_one(value: T | None, message: str) -> T:
    if value is None:
        raise RuntimeError(message)
    return value


def import_facturas(db: Session) -> int:
    material = require_one(
        db.scalar(select(Material).where(Material.nombre == "Cemento Portland")),
        "No existe el material Cemento Portland. Ejecuta primero python -m app.operations.bootstrap.seed.",
    )
    presentacion = require_one(
        db.scalar(
            select(Presentacion).where(
                Presentacion.material_id == material.id,
                Presentacion.nombre_presentacion == "Bolsa 25 kg",
            )
        ),
        "No existe la presentacion Bolsa 25 kg para Cemento Portland. Ejecuta primero python -m app.operations.bootstrap.seed.",
    )
    fuente = require_one(
        db.scalar(select(Fuente).where(Fuente.nombre == "Factura compra")),
        "No existe la fuente Factura compra. Ejecuta primero python -m app.operations.bootstrap.seed.",
    )

    inserted = 0
    for numero_comprobante, fecha, precio_original in FACTURAS_CEMENTO_25KG:
        exists_by_comprobante = db.scalar(
            select(PrecioHistorico).where(
                PrecioHistorico.fuente_id == fuente.id,
                PrecioHistorico.numero_comprobante == numero_comprobante,
            )
        )
        if exists_by_comprobante is not None:
            continue

        exists_by_observacion = db.scalar(
            select(PrecioHistorico).where(
                PrecioHistorico.material_id == material.id,
                PrecioHistorico.presentacion_id == presentacion.id,
                PrecioHistorico.fuente_id == fuente.id,
                PrecioHistorico.fecha == fecha,
                PrecioHistorico.precio_original == precio_original,
            )
        )
        if exists_by_observacion is not None:
            continue

        precio_normalizado = calcular_precio_normalizado(precio_original, Decimal(presentacion.cantidad_base))
        db.add(
            PrecioHistorico(
                material_id=material.id,
                presentacion_id=presentacion.id,
                fuente_id=fuente.id,
                fecha=fecha,
                precio_original=precio_original,
                precio_normalizado=precio_normalizado,
                moneda="ARS",
                numero_comprobante=numero_comprobante,
                observaciones="Factura real cemento bolsa 25 kg",
            )
        )
        inserted += 1

    return inserted


def main() -> None:
    with SessionLocal() as db:
        inserted = import_facturas(db)
        db.commit()
        print(f"Facturas cemento importadas: {inserted}")


if __name__ == "__main__":
    main()
