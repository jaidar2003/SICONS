from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.seed import get_or_create_fuente, get_or_create_material, get_or_create_presentacion
from app.db.session import SessionLocal
from app.models import Fuente, Material, PrecioHistorico, Presentacion
from app.services.pricing import calcular_precio_normalizado


WORKBOOK_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
EXCEL_EPOCH = date(1899, 12, 30)


@dataclass(frozen=True)
class ExcelPrecio:
    fecha: date
    empresa: str
    numero_comprobante: str
    articulo: str
    precio_original: Decimal
    precio_normalizado: Decimal


@dataclass(frozen=True)
class ImportSummary:
    inserted: int
    updated: int
    skipped_duplicate_in_workbook: int
    skipped_blank_or_invalid: int


def cell_column(cell_ref: str) -> str:
    return "".join(char for char in cell_ref if char.isalpha())


def normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().split())


def read_cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value = cell.find("m:v", WORKBOOK_NS)
    if cell_type == "s" and value is not None:
        return shared_strings[int(value.text or "0")]
    if cell_type == "inlineStr":
        text = cell.find("m:is/m:t", WORKBOOK_NS)
        return text.text if text is not None else ""
    return value.text if value is not None else ""


def load_shared_strings(workbook: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    return [
        "".join(text.text or "" for text in shared_string.findall(".//m:t", WORKBOOK_NS))
        for shared_string in root.findall("m:si", WORKBOOK_NS)
    ]


def worksheet_path(workbook: ZipFile, sheet_name: str) -> str:
    workbook_root = ET.fromstring(workbook.read("xl/workbook.xml"))
    relationships_root = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships_root.findall("rel:Relationship", REL_NS)
    }

    for sheet in workbook_root.findall("m:sheets/m:sheet", WORKBOOK_NS):
        if sheet.attrib["name"] != sheet_name:
            continue
        relationship_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        target = relationships[relationship_id].lstrip("/")
        return f"xl/{target}"

    available = ", ".join(sheet.attrib["name"] for sheet in workbook_root.findall("m:sheets/m:sheet", WORKBOOK_NS))
    raise RuntimeError(f"No existe la hoja {sheet_name!r}. Hojas disponibles: {available}")


def parse_decimal(value: str) -> Decimal:
    try:
        return Decimal(value.strip().replace(",", "."))
    except (AttributeError, InvalidOperation) as exc:
        raise ValueError(f"Valor decimal invalido: {value!r}") from exc


def parse_excel_date(value: str) -> date:
    stripped = value.strip()
    if not stripped:
        raise ValueError("Fecha vacia")
    try:
        return EXCEL_EPOCH + timedelta(days=int(Decimal(stripped)))
    except InvalidOperation:
        return datetime.fromisoformat(stripped).date()


def normalize_invoice(value: str) -> str:
    stripped = value.strip()
    if "-" not in stripped:
        return stripped
    branch, number = stripped.split("-", 1)
    if branch.isdigit() and number.isdigit():
        return f"{int(branch):04d}-{int(number):08d}"
    return stripped


def article_metadata(articulo: str) -> tuple[str, str, Decimal, str]:
    normalized = normalize_header(articulo)
    if normalized == "cemento cpc40 bol 50 kg":
        return "Cemento Portland", "Bolsa 50 kg", Decimal("50"), "kg"
    if normalized == "cemento cpc40 x 25 kg":
        return "Cemento Portland", "Bolsa 25 kg", Decimal("25"), "kg"
    raise ValueError(f"Articulo no reconocido: {articulo!r}")


def iter_excel_precios(path: Path, sheet_name: str = "Holcim") -> tuple[list[ExcelPrecio], int]:
    precios: list[ExcelPrecio] = []
    skipped_invalid = 0

    with ZipFile(path) as workbook:
        shared_strings = load_shared_strings(workbook)
        sheet_root = ET.fromstring(workbook.read(worksheet_path(workbook, sheet_name)))
        rows = sheet_root.findall("m:sheetData/m:row", WORKBOOK_NS)
        if not rows:
            return precios, 0

        header_cells = {
            cell_column(cell.attrib.get("r", "")): normalize_header(read_cell_value(cell, shared_strings))
            for cell in rows[0].findall("m:c", WORKBOOK_NS)
        }
        headers = {header: column for column, header in header_cells.items() if header}
        required_headers = {
            "fecha": "fecha",
            "empresa": "empresa",
            "nº factura": "numero_comprobante",
            "articulo": "articulo",
            "artículo": "articulo",
            "px lista c/iva": "precio_original",
            "precio normalizado": "precio_normalizado",
        }
        column_by_field: dict[str, str] = {}
        for header, field in required_headers.items():
            if header in headers:
                column_by_field[field] = headers[header]

        missing = {"fecha", "empresa", "numero_comprobante", "articulo", "precio_original"} - set(column_by_field)
        if missing:
            raise RuntimeError(f"Faltan columnas requeridas en {path}: {', '.join(sorted(missing))}")

        for row in rows[1:]:
            values = {
                cell_column(cell.attrib.get("r", "")): read_cell_value(cell, shared_strings).strip()
                for cell in row.findall("m:c", WORKBOOK_NS)
            }
            if not any(values.values()):
                continue
            try:
                articulo = values.get(column_by_field["articulo"], "")
                _, _, cantidad_base, _ = article_metadata(articulo)
                precio_original = parse_decimal(values.get(column_by_field["precio_original"], ""))
                precio_normalizado = calcular_precio_normalizado(precio_original, cantidad_base)
                precios.append(
                    ExcelPrecio(
                        fecha=parse_excel_date(values.get(column_by_field["fecha"], "")),
                        empresa=values.get(column_by_field["empresa"], ""),
                        numero_comprobante=normalize_invoice(values.get(column_by_field["numero_comprobante"], "")),
                        articulo=articulo,
                        precio_original=precio_original.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                        precio_normalizado=precio_normalizado.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
                    )
                )
            except ValueError:
                skipped_invalid += 1

    return precios, skipped_invalid


def upsert_precio(
    db: Session,
    *,
    precio: ExcelPrecio,
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
                observaciones=f"Importado desde db/sicons.xlsx - {precio.empresa} - {precio.articulo}",
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
    )
    if not changed:
        return "unchanged"

    existing.material_id = material.id
    existing.presentacion_id = presentacion.id
    existing.fecha = precio.fecha
    existing.precio_original = precio.precio_original
    existing.precio_normalizado = precio.precio_normalizado
    existing.moneda = "ARS"
    existing.observaciones = f"Actualizado desde db/sicons.xlsx - {precio.empresa} - {precio.articulo}"
    return "updated"


def import_sicons_excel(db: Session, path: Path = Path("db/sicons.xlsx")) -> ImportSummary:
    fuente = get_or_create_fuente(
        db,
        nombre="Factura compra",
        tipo_fuente="factura",
        descripcion="Comprobantes cargados desde compras propias",
    )
    material = get_or_create_material(
        db,
        nombre="Cemento Portland",
        categoria="Materiales de obra",
        marca="Holcim",
        unidad_base="kg",
        descripcion="Cemento CPC40 Holcim importado desde facturas",
    )

    presentaciones: dict[str, Presentacion] = {}
    for articulo in ("CEMENTO CPC40 BOL 50 KG", "CEMENTO CPC40 X 25 KG"):
        _, nombre_presentacion, cantidad_base, unidad_base = article_metadata(articulo)
        presentaciones[articulo] = get_or_create_presentacion(
            db,
            material=material,
            nombre_presentacion=nombre_presentacion,
            cantidad_base=cantidad_base,
            unidad_presentacion=unidad_base,
        )

    precios, skipped_invalid = iter_excel_precios(path)
    seen_invoices: set[str] = set()
    inserted = 0
    updated = 0
    skipped_duplicate = 0

    for precio in precios:
        if precio.numero_comprobante in seen_invoices:
            skipped_duplicate += 1
            continue
        seen_invoices.add(precio.numero_comprobante)

        presentacion = presentaciones[precio.articulo]
        result = upsert_precio(db, precio=precio, material=material, presentacion=presentacion, fuente=fuente)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1

    return ImportSummary(
        inserted=inserted,
        updated=updated,
        skipped_duplicate_in_workbook=skipped_duplicate,
        skipped_blank_or_invalid=skipped_invalid,
    )


def main() -> None:
    with SessionLocal() as db:
        summary = import_sicons_excel(db)
        db.commit()
        print(f"Precios insertados: {summary.inserted}")
        print(f"Precios actualizados: {summary.updated}")
        print(f"Duplicados omitidos dentro del Excel: {summary.skipped_duplicate_in_workbook}")
        print(f"Filas vacias o invalidas omitidas: {summary.skipped_blank_or_invalid}")


if __name__ == "__main__":
    main()
