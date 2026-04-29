from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed import get_or_create_fuente, get_or_create_material, get_or_create_presentacion
from app.db.session import SessionLocal
from app.models import Fuente, Material, PrecioHistorico, Presentacion
from app.services.pricing import calcular_precio_normalizado


@dataclass(frozen=True)
class PastinaRow:
    fecha: date
    empresa: str
    numero_comprobante: str
    articulo: str
    precio_sin_iva: Decimal
    precio_con_iva: Decimal


@dataclass(frozen=True)
class PastinaPrecio:
    fecha: date
    empresa: str
    numero_comprobante: str
    articulos: tuple[str, ...]
    precio_sin_iva: Decimal
    precio_original: Decimal
    precio_normalizado: Decimal


@dataclass(frozen=True)
class ImportSummary:
    inserted: int
    updated: int
    unchanged: int
    skipped_duplicate_invoice_rows: int


RAW_ROWS = (
    ("13/02/2026", "Proveedor", "63-16764", "PASTINA BLENDA X 1 KG BOX", "$2.213,31", "$2.678,11"),
    ("13/02/2026", "Proveedor", "63-16764", "PASTINA TALCO X 1 KG BOX", "$2.213,31", "$2.678,11"),
    ("01/09/2025", "Proveedor", "63-15004", "PASTINA BRUMAX 1 K", "$1.998,04", "$2.417,63"),
    ("01/09/2025", "Proveedor", "63-15004", "PASTINA MERCURIO X 1 K", "$1.998,04", "$2.417,63"),
    ("01/09/2025", "Proveedor", "63-15004", "PASTUNA HULLA X 1 K", "$1.998,04", "$2.417,63"),
    ("01/09/2025", "Proveedor", "63-15004", "PASTINA TEJA X 1K", "$1.998,04", "$2.417,63"),
    ("28/04/2025", "Proveedor", "63-13634", "PASTINA FLUIDA PN BLENDA 1 KG", "$1.958,85", "$2.370,21"),
    ("25/02/2025", "Proveedor", "63-13008", "PASTINA FLUIDA PN BRUMA", "$1.958,85", "$2.370,21"),
    ("06/02/2025", "Proveedor", "63-12744", "PASTINA TALCO X 1 K", "$1.958,85", "$2.370,21"),
    ("04-11-24", "Proveedor", "63-11655", "PASTINA SILEX X 1 K", "$1.883,61", "$2.279,17"),
    ("14-03-24", "Proveedor", "63-9601", "PASTINA BLENDA X 1 KG", "$1.311,00", "$1.586,31"),
    ("14-03-24", "Proveedor", "63-9601", "PASTINA HULLA X 1 KG", "$1.311,00", "$1.586,31"),
    ("09-11-23", "Proveedor", "63-8208", "PASTINA TALCO X 1 KG", "$648,95", "$785,23"),
    ("09-11-23", "Proveedor", "63-8208", "PASTINA BLENDA X 1 KG", "$648,95", "$785,23"),
    ("09-11-23", "Proveedor", "63-8208", "PASTINA COBRE X 1 KG", "$648,95", "$785,23"),
    ("09-11-23", "Proveedor", "63-8208", "PASTINA CAOBA X 1 KG", "$648,95", "$785,23"),
    ("09-11-23", "Proveedor", "63-8208", "PASTINA HULLA X 1 KG", "$648,95", "$785,23"),
    ("11-04-23", "Proveedor", "63-5932", "PASTINA BRUMA X 1 KG", "$321,69", "$389,24"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA TALCO X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA BLENDA X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA COBRE X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA BRUMA X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA CAOBA X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA MERCURIO X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA SILEX X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA BOREAL X 1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA HULLA X1 KG", "$309,32", "$374,28"),
    ("02-02-23", "Proveedor", "63-05303", "PASTINA TEJA X 1 KG", "$309,32", "$374,28"),
    ("29-09-22", "Proveedor", "0063-00003809", "PASTINA TALCO X 1 K", "$213,53", "$258,37"),
    ("29-09-22", "Proveedor", "0083-00003809", "PASTINA OLIVINA X 1 K", "$213,53", "$258,37"),
    ("09-08-22", "Proveedor", "0063-00002750", "PASTINA HULLA X 1 K", "$147,92", "$178,98"),
    ("02-06-22", "Proveedor", "0063-00001767", "PASTINA FLUIDA BRUMA X 1KG. BOX", "$155,71", "$188,41"),
    ("02-06-22", "Proveedor", "0063-00001767", "PASTINA FLUIDA SILEX X 1 KG. BOX", "$155,71", "$188,41"),
    ("02-06-22", "Proveedor", "0063-00001767", "PASTINA FLUIDA HULLA X 1 KG. BOX", "$155,71", "$188,41"),
    ("26-05-22", "Proveedor", "0063-00001647", "PASTINA AP PERLA X 1 KG,", "$256,03", "$309,80"),
    ("26-05-22", "Proveedor", "0063-00001647", "PASTINA AP CEMENTO X 1 KG,", "$256,03", "$309,80"),
    ("26-05-22", "Proveedor", "0063-00001647", "PASTINA AP CASTANO X 1 KG", "$256,03", "$309,80"),
    ("26-05-22", "Proveedor", "0063-00001647", "PASTINA AP VISON 1 KG", "$256,03", "$309,80"),
    ("14-02-22", "Proveedor", "0063-00000243", "PASTINA FLUIDA PN TALCO X 1 KG.", "$130,35", "$157,72"),
    ("14-02-22", "Proveedor", "0063-00000243", "PASTINA FLUIDA PN BLENDA X 1 KG.", "$130,35", "$157,72"),
)


def parse_decimal(value: str) -> Decimal:
    normalized = value.strip().replace("$", "").replace(".", "").replace(",", ".")
    return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    stripped = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha invalida: {value!r}")


def normalize_invoice(value: str) -> str:
    stripped = value.strip()
    if "-" not in stripped:
        return stripped
    branch, number = stripped.split("-", 1)
    if branch.isdigit() and number.isdigit():
        return f"{int(branch):04d}-{int(number):08d}"
    return stripped


def build_rows() -> list[PastinaRow]:
    return [
        PastinaRow(
            fecha=parse_date(fecha),
            empresa=empresa,
            numero_comprobante=normalize_invoice(numero_comprobante),
            articulo=articulo,
            precio_sin_iva=parse_decimal(precio_sin_iva),
            precio_con_iva=parse_decimal(precio_con_iva),
        )
        for fecha, empresa, numero_comprobante, articulo, precio_sin_iva, precio_con_iva in RAW_ROWS
    ]


def grouped_prices() -> tuple[list[PastinaPrecio], int]:
    rows_by_invoice: dict[str, list[PastinaRow]] = {}
    for row in build_rows():
        rows_by_invoice.setdefault(row.numero_comprobante, []).append(row)

    prices: list[PastinaPrecio] = []
    skipped_duplicate_rows = 0
    for rows in rows_by_invoice.values():
        first = rows[0]
        for row in rows[1:]:
            if (
                row.fecha != first.fecha
                or row.empresa != first.empresa
                or row.precio_sin_iva != first.precio_sin_iva
                or row.precio_con_iva != first.precio_con_iva
            ):
                raise ValueError(f"La factura {first.numero_comprobante} tiene valores inconsistentes")
            skipped_duplicate_rows += 1

        precio_normalizado = calcular_precio_normalizado(first.precio_con_iva, Decimal("1"))
        prices.append(
            PastinaPrecio(
                fecha=first.fecha,
                empresa=first.empresa,
                numero_comprobante=first.numero_comprobante,
                articulos=tuple(row.articulo for row in rows),
                precio_sin_iva=first.precio_sin_iva,
                precio_original=first.precio_con_iva,
                precio_normalizado=precio_normalizado.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            )
        )

    return prices, skipped_duplicate_rows


def observaciones(precio: PastinaPrecio) -> str:
    articulos = "; ".join(precio.articulos)
    return (
        f"Importado desde carga manual Proveedor Pastina 1 kg - {precio.empresa} - "
        f"Px lista s/IVA {precio.precio_sin_iva} - Articulos: {articulos}"
    )


def upsert_precio(
    db: Session,
    *,
    precio: PastinaPrecio,
    material: Material,
    presentacion: Presentacion,
    fuente: Fuente,
) -> str:
    existing = db.scalar(
        select(PrecioHistorico).where(
            PrecioHistorico.fuente_id == fuente.id,
            PrecioHistorico.numero_comprobante == precio.numero_comprobante,
        )
    )
    if existing is None:
        db.add(
            PrecioHistorico(
                material_id=material.id,
                presentacion_id=presentacion.id,
                fuente_id=fuente.id,
                fecha=precio.fecha,
                precio_original=precio.precio_original,
                precio_normalizado=precio.precio_normalizado,
                moneda="ARS",
                numero_comprobante=precio.numero_comprobante,
                observaciones=observaciones(precio),
            )
        )
        return "inserted"

    changed = (
        existing.material_id != material.id
        or existing.presentacion_id != presentacion.id
        or existing.fecha != precio.fecha
        or existing.precio_original != precio.precio_original
        or existing.precio_normalizado != precio.precio_normalizado
        or existing.moneda != "ARS"
        or existing.observaciones != observaciones(precio)
    )
    if not changed:
        return "unchanged"

    existing.material_id = material.id
    existing.presentacion_id = presentacion.id
    existing.fecha = precio.fecha
    existing.precio_original = precio.precio_original
    existing.precio_normalizado = precio.precio_normalizado
    existing.moneda = "ARS"
    existing.observaciones = observaciones(precio)
    return "updated"


def import_pastina(db: Session) -> ImportSummary:
    fuente = get_or_create_fuente(
        db,
        nombre="Factura compra Proveedor",
        tipo_fuente="factura",
        descripcion="Comprobantes de compra Proveedor para pastina",
    )
    material = get_or_create_material(
        db,
        nombre="Pastina",
        categoria="Revestimientos",
        marca="Proveedor",
        unidad_base="kg",
        descripcion="Pastina para juntas de revestimientos",
    )
    presentacion = get_or_create_presentacion(
        db,
        material=material,
        nombre_presentacion="Unidad 1 kg",
        cantidad_base=Decimal("1"),
        unidad_presentacion="unidad",
    )

    prices, skipped_duplicate_rows = grouped_prices()
    inserted = 0
    updated = 0
    unchanged = 0

    for precio in prices:
        result = upsert_precio(db, precio=precio, material=material, presentacion=presentacion, fuente=fuente)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        else:
            unchanged += 1

    return ImportSummary(
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        skipped_duplicate_invoice_rows=skipped_duplicate_rows,
    )


def main() -> None:
    with SessionLocal() as db:
        summary = import_pastina(db)
        db.commit()
        print(f"Precios Proveedor Pastina insertados: {summary.inserted}")
        print(f"Precios Proveedor Pastina actualizados: {summary.updated}")
        print(f"Precios Proveedor Pastina sin cambios: {summary.unchanged}")
        print(f"Filas omitidas por factura duplicada: {summary.skipped_duplicate_invoice_rows}")


if __name__ == "__main__":
    main()
