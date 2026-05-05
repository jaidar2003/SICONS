from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.operations.bootstrap.export_cemento_canonico import (
    EXPORT_COLUMNS,
    anonymize_comprobante,
    build_export_rows,
    compare_monthly_series,
    resolve_source_name,
    validate_export_rows,
    write_csv,
)


def make_record(
    *,
    fecha: date,
    numero_comprobante: str,
    precio_original: str = "6250.00",
    precio_normalizado: str = "250.0000",
    moneda: str = "ARS",
    observaciones: str = "Importado desde db/sicons.xlsx - Holcim - CEMENTO CPC40 X 25 KG",
    fuente_nombre: str = "Historico canonico Cemento Portland",
):
    return SimpleNamespace(
        id=1,
        fecha=fecha,
        numero_comprobante=numero_comprobante,
        precio_original=Decimal(precio_original),
        precio_normalizado=Decimal(precio_normalizado),
        moneda=moneda,
        observaciones=observaciones,
        fuente=SimpleNamespace(nombre=fuente_nombre),
        material=SimpleNamespace(nombre="Cemento Portland", unidad_base="kg"),
    )


def make_continuous_records(months: int = 24) -> list[SimpleNamespace]:
    records = []
    year = 2022
    month = 1
    for index in range(months):
        records.append(
            make_record(
                fecha=date(year, month, 3),
                numero_comprobante=f"0256-{index + 1:08d}",
                precio_original=f"{Decimal('5000.00') + Decimal(index):.2f}",
                precio_normalizado=f"{Decimal('200.0000') + (Decimal(index) / Decimal('25')):.4f}",
            )
        )
        month += 1
        if month == 13:
            month = 1
            year += 1
    return records


def test_exporta_columnas_exactas_y_ordenadas(tmp_path) -> None:
    rows = build_export_rows(make_continuous_records())
    output = tmp_path / "cemento.csv"

    write_csv(rows, output)

    lines = output.read_text(encoding="utf-8").splitlines()
    assert lines[0].split(",") == list(EXPORT_COLUMNS)
    assert rows[0].fecha <= rows[-1].fecha


def test_formato_fechas_y_decimales_y_campos_forzados(tmp_path) -> None:
    rows = build_export_rows(make_continuous_records())
    output = tmp_path / "cemento.csv"

    write_csv(rows, output)

    first_data = output.read_text(encoding="utf-8").splitlines()[1].split(",")
    assert first_data[0] == "2022-01-03"
    assert first_data[4] == "5000.00"
    assert first_data[5] == "200.0000"
    assert first_data[7] == "REAL"
    assert first_data[8] == ""


def test_anonimizacion_estable() -> None:
    comprobante = "0256-00044369"

    first = anonymize_comprobante(comprobante)
    second = anonymize_comprobante(comprobante)

    assert first == second
    assert first.startswith("CMT-")
    assert first != comprobante


def test_build_export_rows_anonimiza_comprobantes() -> None:
    rows = build_export_rows(make_continuous_records(), anonimizar_comprobante=True)

    assert rows[0].numero_comprobante.startswith("CMT-")
    assert rows[0].origen_dato == "REAL"
    assert rows[0].metodo_estimacion == ""


def test_detecta_duplicados_por_numero_comprobante_exportado() -> None:
    rows = build_export_rows(
        [
            make_record(fecha=date(2022, 1, 3), numero_comprobante="0256-00000001"),
            make_record(fecha=date(2022, 2, 3), numero_comprobante="0256-00000001"),
        ]
        + make_continuous_records(months=22)
    )

    with pytest.raises(ValueError, match="Duplicado detectado"):
        validate_export_rows(rows)


def test_detecta_precios_invalidos() -> None:
    records = make_continuous_records()
    records[0] = make_record(fecha=date(2022, 1, 3), numero_comprobante="0256-00000001", precio_original="0.00")
    rows = build_export_rows(records)

    with pytest.raises(ValueError, match="precio_original invalido"):
        validate_export_rows(rows)


def test_detecta_huecos_mensuales() -> None:
    records = make_continuous_records(months=24)
    del records[10]
    rows = build_export_rows(records)

    with pytest.raises(ValueError, match="huecos mensuales"):
        validate_export_rows(rows)


def test_falla_si_no_hay_datos_suficientes() -> None:
    rows = build_export_rows(make_continuous_records(months=12))

    with pytest.raises(ValueError, match="No hay datos suficientes"):
        validate_export_rows(rows)


def test_falla_si_no_se_puede_distinguir_fuente_canonica() -> None:
    records = [
        make_record(fecha=date(2022, 1, 3), numero_comprobante="0256-00000001", fuente_nombre="Factura compra"),
        make_record(
            fecha=date(2022, 2, 3),
            numero_comprobante="0256-00000002",
            fuente_nombre="Historico canonico Cemento Portland",
        ),
    ]

    with pytest.raises(ValueError, match="No se puede distinguir con confianza la fuente historica canonica"):
        resolve_source_name(records, None)


def test_compare_monthly_series_ok() -> None:
    records = make_continuous_records()
    rows = build_export_rows(records)

    assert compare_monthly_series(rows, records) is True
