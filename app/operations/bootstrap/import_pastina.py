from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.bootstrap.common import get_or_create_fuente, get_or_create_material, get_or_create_presentacion
from app.shared.database.session import SessionLocal


@dataclass(frozen=True)
class PastinaRow:
    fecha: date
    empresa: str
    origen: str
    numero_comprobante: str
    articulo: str
    precio_sin_iva: Decimal
    precio_con_iva: Decimal


@dataclass(frozen=True)
class PastinaPrecio:
    fecha: date
    empresa: str
    origen: str
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
    deleted_previous_rows: int


RAW_ROWS = (
    ("01/01/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$124,50", "$150,64"),
    ("14/02/2022", "SIKA", "63-00243", "KLAUKOL PASTINA FLUIDA PN", "$130,35", "$157,72"),
    ("01/03/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$140,59", "$170,12"),
    ("01/04/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$149,03", "$180,33"),
    ("01/05/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$154,94", "$187,48"),
    ("02/06/2022", "SIKA", "63-01767", "KLAUKOL PASTINA FLUIDA", "$155,71", "$188,41"),
    ("01/07/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$169,86", "$205,53"),
    ("01/08/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$181,75", "$219,92"),
    ("29/09/2022", "SIKA", "63-03809", "PASTINA KLAUKOL TALCO", "$213,53", "$258,37"),
    ("01/10/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$234,49", "$283,73"),
    ("01/11/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$245,98", "$297,63"),
    ("01/12/2022", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$258,52", "$312,81"),
    ("01/01/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$274,03", "$331,58"),
    ("02/02/2023", "SIKA", "63-05303", "PASTINA KLAUKOL TALCO", "$309,32", "$374,28"),
    ("01/03/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$341,50", "$413,22"),
    ("01/04/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$370,19", "$447,93"),
    ("01/05/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$399,07", "$482,87"),
    ("01/06/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$423,01", "$511,84"),
    ("01/07/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$449,66", "$544,09"),
    ("01/08/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$505,41", "$611,55"),
    ("01/09/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$569,60", "$689,22"),
    ("01/10/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$616,88", "$746,43"),
    ("09/11/2023", "SIKA", "63-8208", "PASTINA TALCO X 1 KG", "$648,95", "$785,23"),
    ("01/12/2023", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$868,16", "$1050,47"),
    ("01/01/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1047,00", "$1266,87"),
    ("01/02/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1185,21", "$1434,10"),
    ("14/03/2024", "SIKA", "63-9601", "PASTINA BLENDA X 1 KG", "$1311,00", "$1586,31"),
    ("01/04/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1402,11", "$1696,55"),
    ("01/05/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1454,58", "$1760,04"),
    ("01/06/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1521,50", "$1841,01"),
    ("01/07/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1582,36", "$1914,65"),
    ("01/08/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1648,81", "$1995,06"),
    ("01/09/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1706,52", "$2064,89"),
    ("01/10/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1752,59", "$2120,64"),
    ("04/11/2024", "SIKA", "63-11655", "PASTINA SILEX X 1 K", "$1883,61", "$2279,17"),
    ("01/12/2024", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1934,47", "$2340,71"),
    ("01/01/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1977,02", "$2392,20"),
    ("25/02/2025", "SIKA", "63-13008", "PASTINA FLUIDA PN BRUMA", "$1958,85", "$2370,21"),
    ("01/03/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1967,28", "$2380,41"),
    ("01/04/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1973,92", "$2388,44"),
    ("01/05/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1977,45", "$2392,72"),
    ("01/06/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1981,10", "$2397,13"),
    ("01/07/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1985,45", "$2402,40"),
    ("01/08/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$1989,85", "$2407,72"),
    ("01/09/2025", "SIKA", "63-15004", "PASTINA BRUMAX 1 K", "$1998,04", "$2417,63"),
    ("01/10/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$2044,00", "$2473,24"),
    ("01/11/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$2095,10", "$2535,07"),
    ("01/12/2025", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$2153,76", "$2606,05"),
    ("01/01/2026", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$2216,21", "$2681,62"),
    ("13/02/2026", "SIKA", "63-16764", "PASTINA BLENDA X 1 KG", "$2213,31", "$2678,11"),
    ("01/03/2026", "SIKA", "ESTIMADO", "PASTINA KLAUKOL", "$2288,57", "$2769,17"),
)


def parse_decimal(value: str) -> Decimal:
    normalized = value.strip().replace("$", "").replace(".", "").replace(",", ".")
    return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    stripped = value.strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%y", "%d-%m-%Y"):
        try:
            return datetime.strptime(stripped, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Fecha invalida: {value!r}")


def normalize_invoice(value: str) -> str:
    stripped = value.strip()
    if stripped.upper() == "ESTIMADO":
        return "ESTIMADO"
    if "-" not in stripped:
        return stripped
    branch, number = stripped.split("-", 1)
    if branch.isdigit() and number.isdigit():
        return f"{int(branch):04d}-{int(number):08d}"
    return stripped


def build_rows() -> list[PastinaRow]:
    rows: list[PastinaRow] = []
    for fecha, empresa, numero_comprobante, articulo, precio_sin_iva, precio_con_iva in RAW_ROWS:
        fecha_parseada = parse_date(fecha)
        numero_normalizado = normalize_invoice(numero_comprobante)
        origen = "estimado" if numero_normalizado == "ESTIMADO" else "real"
        if origen == "estimado":
            numero_normalizado = f"ESTIMADO-{fecha_parseada.isoformat()}"
        rows.append(
            PastinaRow(
                fecha=fecha_parseada,
                empresa=empresa,
                origen=origen,
                numero_comprobante=numero_normalizado,
                articulo=articulo,
                precio_sin_iva=parse_decimal(precio_sin_iva),
                precio_con_iva=parse_decimal(precio_con_iva),
            )
        )
    return rows


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
                or row.origen != first.origen
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
                origen=first.origen,
                numero_comprobante=first.numero_comprobante,
                articulos=tuple(row.articulo for row in rows),
                precio_sin_iva=first.precio_sin_iva,
                precio_original=first.precio_con_iva,
                precio_normalizado=precio_normalizado.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
            )
        )

    prices.sort(key=lambda item: (item.fecha, item.numero_comprobante))
    return prices, skipped_duplicate_rows


def observaciones(precio: PastinaPrecio) -> str:
    articulos = "; ".join(precio.articulos)
    if precio.origen == "estimado":
        return (
            f"Serie estimada Pastina SIKA 1 kg - {precio.empresa} - "
            f"Px estimado s/IVA {precio.precio_sin_iva} - Articulos: {articulos}"
        )
    return (
        f"Importado desde precios reales Pastina SIKA 1 kg - {precio.empresa} - "
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
                origen_dato=precio.origen.upper(),
                metodo_estimacion="IPC" if precio.origen == "estimado" else None,
                observaciones=observaciones(precio),
            )
        )
        return "inserted"

    origen_dato = precio.origen.upper()
    metodo_estimacion = "IPC" if precio.origen == "estimado" else None
    changed = (
        existing.material_id != material.id
        or existing.presentacion_id != presentacion.id
        or existing.fecha != precio.fecha
        or existing.precio_original != precio.precio_original
        or existing.precio_normalizado != precio.precio_normalizado
        or existing.moneda != "ARS"
        or getattr(existing, "origen_dato", origen_dato) != origen_dato
        or getattr(existing, "metodo_estimacion", metodo_estimacion) != metodo_estimacion
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
    existing.origen_dato = origen_dato
    existing.metodo_estimacion = metodo_estimacion
    existing.observaciones = observaciones(precio)
    return "updated"


def get_or_update_pastina_material(db: Session) -> Material:
    material = db.scalar(select(Material).where(Material.nombre == "Pastina"))
    if material is not None:
        material.categoria = "Revestimientos"
        material.marca = "SIKA"
        material.unidad_base = "kg"
        material.descripcion = "Pastina SIKA para juntas de revestimientos"
        material.activo = True
        db.flush()
        return material

    return get_or_create_material(
        db,
        nombre="Pastina",
        categoria="Revestimientos",
        marca="SIKA",
        unidad_base="kg",
        descripcion="Pastina SIKA para juntas de revestimientos",
    )


def import_pastina(db: Session) -> ImportSummary:
    fuente_real = get_or_create_fuente(
        db,
        nombre="Factura compra SIKA Pastina",
        tipo_fuente="factura",
        descripcion="Comprobantes reales de SIKA para pastina",
    )
    fuente_estimada = get_or_create_fuente(
        db,
        nombre="Estimacion IPC SIKA Pastina",
        tipo_fuente="estimacion",
        descripcion="Serie mensual estimada de SIKA para pastina usando IPC",
    )
    material = get_or_update_pastina_material(db)
    presentacion = get_or_create_presentacion(
        db,
        material=material,
        nombre_presentacion="Unidad 1 kg",
        cantidad_base=Decimal("1"),
        unidad_presentacion="unidad",
    )

    deleted_previous_rows = db.execute(
        delete(PrecioHistorico).where(PrecioHistorico.material_id == material.id)
    ).rowcount or 0

    prices, skipped_duplicate_rows = grouped_prices()
    inserted = 0
    updated = 0
    unchanged = 0

    for precio in prices:
        fuente = fuente_estimada if precio.origen == "estimado" else fuente_real
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
        deleted_previous_rows=deleted_previous_rows,
    )


def main() -> None:
    with SessionLocal() as db:
        summary = import_pastina(db)
        db.commit()
        print(f"Precios SIKA Pastina insertados: {summary.inserted}")
        print(f"Precios SIKA Pastina actualizados: {summary.updated}")
        print(f"Precios SIKA Pastina sin cambios: {summary.unchanged}")
        print(f"Filas previas eliminadas: {summary.deleted_previous_rows}")
        print(f"Filas omitidas por factura duplicada: {summary.skipped_duplicate_invoice_rows}")


if __name__ == "__main__":
    main()
