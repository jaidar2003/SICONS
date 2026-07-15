from datetime import date
from pathlib import Path
from zipfile import ZipFile

import pytest

from app.operations.bootstrap.import_sicons_excel import iter_excel_precios


def write_minimal_workbook(path: Path, *, invoice: str, invoice_date: str) -> None:
    headers = ["Fecha", "Empresa", "Nº Factura", "Articulo", "PX Lista c/IVA"]
    values = [invoice_date, "HOLCIM", invoice, "CEMENTO CPC40 X 25 KG", "4460.53"]

    def row_xml(row_number: int, row_values: list[str]) -> str:
        cells = "".join(
            f'<c r="{column}{row_number}" t="inlineStr"><is><t>{value}</t></is></c>'
            for column, value in zip("ABCDE", row_values, strict=True)
        )
        return f'<row r="{row_number}">{cells}</row>'

    worksheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{row_xml(1, headers)}{row_xml(2, values)}</sheetData>"
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Holcim" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    with ZipFile(path, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", relationships)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)


@pytest.mark.parametrize("invoice", ["0256-00046834", "0256-00046835"])
def test_confirmed_invoice_correction_is_applied_at_excel_import_boundary(tmp_path, invoice) -> None:
    workbook = tmp_path / "sicons.xlsx"
    write_minimal_workbook(workbook, invoice=invoice, invoice_date="2026-11-26")

    prices, skipped = iter_excel_precios(workbook)

    assert skipped == 0
    assert len(prices) == 1
    assert prices[0].numero_comprobante == invoice
    assert prices[0].fecha == date(2025, 11, 26)
