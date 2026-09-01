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
class MembranaRow:
    fecha: date
    empresa: str
    origen: str
    numero_comprobante: str
    articulo: str
    precio_sin_iva: Decimal
    precio_con_iva: Decimal


@dataclass(frozen=True)
class MembranaPrecio:
    fecha: date
    empresa: str
    origen: str
    numero_comprobante: str
    articulo: str
    precio_sin_iva: Decimal
    precio_original: Decimal
    precio_normalizado: Decimal


@dataclass(frozen=True)
class ImportSummary:
    inserted: int
    updated: int
    unchanged: int
    deleted_previous_rows: int


RAW_ROWS = (
    ("01/01/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$7.337,53", "$8.878,41"),
    ("01/02/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$7.682,39", "$9.295,70"),
    ("04/03/2022", "MEGAFLEX", "253-04038", "TECHOS BLANCO 20 KG", "$7.623,70", "$9.224,67"),
    ("05/04/2022", "MEGAFLEX", "253-04307", "TECHOS BLANCO 20 KG", "$7.623,70", "$9.224,67"),
    ("01/05/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$8.157,34", "$9.870,38"),
    ("01/06/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$8.589,68", "$10.393,51"),
    ("01/07/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$9.225,31", "$11.162,63"),
    ("01/08/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$9.871,08", "$11.944,01"),
    ("01/09/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$10.483,09", "$12.684,54"),
    ("01/10/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$11.143,53", "$13.483,67"),
    ("01/11/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$11.689,56", "$14.144,37"),
    ("01/12/2022", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$12.285,73", "$14.865,73"),
    ("01/01/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$13.022,87", "$15.757,67"),
    ("01/02/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$13.882,38", "$16.797,68"),
    ("22/03/2023", "MEGAFLEX", "253-5446", "TECHOS BLANCO 20 KG", "$17.194,64", "$20.805,52"),
    ("01/04/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$21.355,74", "$25.840,45"),
    ("01/05/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$23.021,47", "$27.855,98"),
    ("01/06/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$24.402,75", "$29.527,33"),
    ("01/07/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$25.940,12", "$31.387,55"),
    ("01/08/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$29.156,70", "$35.279,61"),
    ("01/09/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$32.859,47", "$39.759,96"),
    ("01/10/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$35.586,42", "$43.059,57"),
    ("01/11/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$40.137,54", "$48.566,42"),
    ("01/12/2023", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$50.371,11", "$60.949,04"),
    ("01/01/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$60.747,45", "$73.504,41"),
    ("26/02/2024", "MEGAFLEX", "253-6199", "TECHOS BLANCO 20 KG", "$105.934,28", "$128.180,48"),
    ("01/03/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$105.934,28", "$128.180,48"),
    ("01/04/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$115.256,49", "$139.460,36"),
    ("01/05/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$120.097,27", "$145.317,70"),
    ("01/06/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$125.616,89", "$151.996,44"),
    ("01/07/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$130.641,57", "$158.076,30"),
    ("01/08/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$136.128,51", "$164.715,50"),
    ("01/09/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$140.893,02", "$170.480,55"),
    ("01/10/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$144.697,12", "$175.083,52"),
    ("01/11/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$148.170,00", "$179.285,53"),
    ("01/12/2024", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$152.170,45", "$184.126,24"),
    ("01/01/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$155.518,19", "$188.177,01"),
    ("01/02/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$156.414,63", "$189.261,70"),
    ("01/03/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$156.414,63", "$189.261,70"),
    ("01/04/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$156.414,63", "$189.261,70"),
    ("01/05/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$156.414,63", "$189.261,70"),
    ("19/06/2025", "MEGAFLEX", "318-735", "TECHOS BLANCO 20 KG", "$156.414,63", "$189.261,70"),
    ("01/07/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$159.386,50", "$192.857,67"),
    ("01/08/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$162.414,85", "$196.521,97"),
    ("12/09/2025", "MEGAFLEX", "318-986", "TECHOS BLANCO 20 KG", "$160.325,00", "$193.993,24"),
    ("01/10/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$164.012,46", "$198.455,08"),
    ("01/11/2025", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$168.112,78", "$203.416,46"),
    ("22/12/2025", "MEGAFLEX", "318-1311", "TECHOS BLANCO 20 KG", "$166.577,67", "$201.558,98"),
    ("01/01/2026", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$166.577,67", "$201.558,98"),
    ("06/02/2026", "MEGAFLEX", "318-1473", "TECHOS BLANCO 20 KG", "$166.577,67", "$201.558,98"),
    ("01/03/2026", "MEGAFLEX", "ESTIMADO", "TECHOS BLANCO 20KG", "$172.241,31", "$208.411,99"),
    ("01/04/2026", "MEGAFLEX", "318-1706", "TECHOS BLANCO 20 KG", "$166.577,67", "$201.558,98"),
)


def parse_decimal(value: str) -> Decimal:
    normalized = value.strip().replace("$", "").replace(".", "").replace(",", ".")
    return Decimal(normalized).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%d/%m/%Y").date()


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


def build_rows() -> list[MembranaRow]:
    rows: list[MembranaRow] = []
    for fecha, empresa, numero_comprobante, articulo, precio_sin_iva, precio_con_iva in RAW_ROWS:
        fecha_parseada = parse_date(fecha)
        numero_normalizado = normalize_invoice(numero_comprobante)
        origen = "estimado" if numero_normalizado == "ESTIMADO" else "real"
        if origen == "estimado":
            numero_normalizado = f"ESTIMADO-{fecha_parseada.isoformat()}"
        rows.append(
            MembranaRow(
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


def build_prices() -> list[MembranaPrecio]:
    prices: list[MembranaPrecio] = []
    for row in build_rows():
        prices.append(
            MembranaPrecio(
                fecha=row.fecha,
                empresa=row.empresa,
                origen=row.origen,
                numero_comprobante=row.numero_comprobante,
                articulo=row.articulo,
                precio_sin_iva=row.precio_sin_iva,
                precio_original=row.precio_sin_iva,
                precio_normalizado=calcular_precio_normalizado(row.precio_sin_iva, Decimal("20")).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                ),
            )
        )
    prices.sort(key=lambda item: (item.fecha, item.numero_comprobante))
    return prices


def observaciones(precio: MembranaPrecio) -> str:
    if precio.origen == "estimado":
        return (
            f"Serie estimada Membrana Megaflex 20 kg - {precio.empresa} - "
            f"Px estimado s/IVA {precio.precio_sin_iva} - Articulo: {precio.articulo}"
        )
    return (
        f"Importado desde precios reales Membrana Megaflex 20 kg - {precio.empresa} - "
        f"Px lista s/IVA {precio.precio_sin_iva} - Articulo: {precio.articulo}"
    )


def upsert_precio(
    db: Session,
    *,
    precio: MembranaPrecio,
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

    changed = (
        existing.material_id != material.id
        or existing.presentacion_id != presentacion.id
        or existing.fecha != precio.fecha
        or existing.precio_original != precio.precio_original
        or existing.precio_normalizado != precio.precio_normalizado
        or existing.moneda != "ARS"
        or existing.origen_dato != precio.origen.upper()
        or existing.metodo_estimacion != ("IPC" if precio.origen == "estimado" else None)
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
    existing.origen_dato = precio.origen.upper()
    existing.metodo_estimacion = "IPC" if precio.origen == "estimado" else None
    existing.observaciones = observaciones(precio)
    return "updated"


def get_or_update_membrana_material(db: Session) -> Material:
    material = db.scalar(select(Material).where(Material.nombre == "Membrana Megaflex"))
    if material is not None:
        material.categoria = "Impermeabilizantes"
        material.marca = "MEGAFLEX"
        material.unidad_base = "kg"
        material.descripcion = "Membrana liquida Megaflex Techos Blanco en balde de 20 kg"
        material.activo = True
        db.flush()
        return material

    return get_or_create_material(
        db,
        nombre="Membrana Megaflex",
        categoria="Impermeabilizantes",
        marca="MEGAFLEX",
        unidad_base="kg",
        descripcion="Membrana liquida Megaflex Techos Blanco en balde de 20 kg",
    )


def import_membrana_megaflex(db: Session) -> ImportSummary:
    fuente_real = get_or_create_fuente(
        db,
        nombre="Factura compra Megaflex Membrana",
        tipo_fuente="factura",
        descripcion="Comprobantes reales de Megaflex para membrana",
    )
    fuente_estimada = get_or_create_fuente(
        db,
        nombre="Estimacion IPC Megaflex Membrana",
        tipo_fuente="estimacion",
        descripcion="Serie mensual estimada de Megaflex para membrana usando IPC",
    )
    material = get_or_update_membrana_material(db)
    presentacion = get_or_create_presentacion(
        db,
        material=material,
        nombre_presentacion="Balde 20 kg",
        cantidad_base=Decimal("20"),
        unidad_presentacion="balde",
    )

    deleted_previous_rows = db.execute(
        delete(PrecioHistorico).where(PrecioHistorico.material_id == material.id)
    ).rowcount or 0

    inserted = 0
    updated = 0
    unchanged = 0

    for precio in build_prices():
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
        deleted_previous_rows=deleted_previous_rows,
    )


def main() -> None:
    with SessionLocal() as db:
        summary = import_membrana_megaflex(db)
        db.commit()
        print(f"Precios Membrana Megaflex insertados: {summary.inserted}")
        print(f"Precios Membrana Megaflex actualizados: {summary.updated}")
        print(f"Precios Membrana Megaflex sin cambios: {summary.unchanged}")
        print(f"Filas previas eliminadas: {summary.deleted_previous_rows}")


if __name__ == "__main__":
    main()
