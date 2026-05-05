from decimal import Decimal

from sqlalchemy.orm import Session

from app.operations.bootstrap.common import (
    get_or_create_fuente,
    get_or_create_material,
    get_or_create_presentacion,
    get_or_create_usuario,
)
from app.shared.database.session import SessionLocal


def seed(db: Session) -> None:
    cemento = get_or_create_material(
        db,
        nombre="Cemento Portland",
        categoria="Materiales de obra",
        marca="Holcim",
        unidad_base="kg",
        descripcion="Cemento de uso general para construccion",
    )
    get_or_create_presentacion(
        db,
        material=cemento,
        nombre_presentacion="Bolsa 50 kg",
        cantidad_base=Decimal("50"),
        unidad_presentacion="bolsa",
    )
    get_or_create_presentacion(
        db,
        material=cemento,
        nombre_presentacion="Bolsa 25 kg",
        cantidad_base=Decimal("25"),
        unidad_presentacion="bolsa",
    )

    get_or_create_fuente(
        db,
        nombre="Factura compra",
        tipo_fuente="factura",
        descripcion="Comprobantes cargados desde compras propias",
    )
    get_or_create_fuente(
        db,
        nombre="Lista de precios proveedor",
        tipo_fuente="lista_precios",
        descripcion="Listas comerciales informadas por proveedores",
    )
    get_or_create_fuente(
        db,
        nombre="Relevamiento manual",
        tipo_fuente="manual",
        descripcion="Carga manual tomada de comercios o presupuestos",
    )
    get_or_create_usuario(
        db,
        username="admin",
        nombre="Duenio BuildWise",
        password="admin123",
        rol="admin",
    )
    get_or_create_usuario(
        db,
        username="cliente",
        nombre="Cliente demo",
        password="cliente123",
        rol="cliente",
    )


def main() -> None:
    with SessionLocal() as db:
        seed(db)
        db.commit()


if __name__ == "__main__":
    main()
