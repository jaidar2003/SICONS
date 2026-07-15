from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.operations.data_quality import correct_future_cement_invoices as operation
from app.operations.data_quality.cement_invoice_dates import normalize_confirmed_invoice_date


def build_row(invoice: str, fecha: date = operation.EXPECTED_OLD_DATE):
    price = SimpleNamespace(
        id=34 if invoice.endswith("34") else 35,
        numero_comprobante=invoice,
        fecha=fecha,
        precio_original=Decimal("4460.53"),
        precio_normalizado=Decimal("178.4213"),
        moneda="ARS",
        origen_dato="REAL",
        created_at=datetime(2026, 5, 5, 14, 16, tzinfo=UTC),
    )
    source = SimpleNamespace(nombre="Factura compra")
    material = SimpleNamespace(nombre="Cemento Portland")
    presentation = SimpleNamespace(nombre_presentacion="Bolsa 25 kg")
    return price, source, material, presentation


def build_db(rows):
    db = MagicMock()
    db.execute.return_value = rows
    records_by_id = {row[0].id: row[0] for row in rows}
    db.get.side_effect = lambda _model, record_id: records_by_id.get(record_id)
    return db


def test_confirmed_invoice_dates_are_normalized_without_changing_other_invoices() -> None:
    assert normalize_confirmed_invoice_date("0256-00046834", date(2026, 11, 26)) == date(2025, 11, 26)
    assert normalize_confirmed_invoice_date("0256-00046835", date(2026, 11, 26)) == date(2025, 11, 26)
    assert normalize_confirmed_invoice_date("0256-00046836", date(2025, 11, 26)) == date(2025, 11, 26)


def test_dry_run_preserves_records_and_reports_complete_evidence() -> None:
    rows = [build_row("0256-00046834"), build_row("0256-00046835")]
    db = build_db(rows)

    evidence = operation.correct_records(db, apply=False)

    assert [item.invoice for item in evidence] == ["0256-00046834", "0256-00046835"]
    assert {item.old_date for item in evidence} == {date(2026, 11, 26)}
    assert {item.new_date for item in evidence} == {date(2025, 11, 26)}
    assert {item.presentation for item in evidence} == {"Bolsa 25 kg"}
    assert {item.original_price for item in evidence} == {Decimal("4460.53")}
    assert all(item.status == "pending" for item in evidence)
    db.get.assert_not_called()
    db.commit.assert_not_called()


def test_apply_changes_only_dates_and_registers_audit(monkeypatch) -> None:
    rows = [build_row("0256-00046834"), build_row("0256-00046835")]
    db = build_db(rows)
    audit_calls: list[dict] = []
    monkeypatch.setattr(operation, "register_audit_log", lambda _db, **kwargs: audit_calls.append(kwargs))

    operation.correct_records(db, apply=True)

    assert {row[0].fecha for row in rows} == {date(2025, 11, 26)}
    assert {row[0].precio_original for row in rows} == {Decimal("4460.53")}
    assert len(audit_calls) == 2
    assert {call["accion"] for call in audit_calls} == {"DATA_QUALITY_CORRECTED"}
    assert {call["cambios"]["valor_anterior"] for call in audit_calls} == {"2026-11-26"}
    assert {call["cambios"]["valor_nuevo"] for call in audit_calls} == {"2025-11-26"}
    db.commit.assert_called_once_with()


def test_apply_is_idempotent_for_already_corrected_records(monkeypatch) -> None:
    rows = [
        build_row("0256-00046834", date(2025, 11, 26)),
        build_row("0256-00046835", date(2025, 11, 26)),
    ]
    db = build_db(rows)
    audit = MagicMock()
    monkeypatch.setattr(operation, "register_audit_log", audit)

    evidence = operation.correct_records(db, apply=True)

    assert all(item.status == "unchanged" for item in evidence)
    audit.assert_not_called()
    db.get.assert_not_called()
    db.commit.assert_called_once_with()


@pytest.mark.parametrize(
    ("attribute", "unexpected", "message"),
    [
        ("source", "Otra fuente", "Fuente inesperada"),
        ("material", "Pastina", "Material inesperado"),
        ("presentation", "Bolsa 50 kg", "Presentacion inesperada"),
        ("origin", "ESTIMADO", "Origen inesperado"),
        ("date", date(2024, 1, 1), "Fecha inesperada"),
    ],
)
def test_fails_closed_when_preconditions_do_not_match(attribute, unexpected, message) -> None:
    rows = [build_row("0256-00046834"), build_row("0256-00046835")]
    price, source, material, presentation = rows[0]
    targets = {
        "source": (source, "nombre"),
        "material": (material, "nombre"),
        "presentation": (presentation, "nombre_presentacion"),
        "origin": (price, "origen_dato"),
        "date": (price, "fecha"),
    }
    target, field = targets[attribute]
    setattr(target, field, unexpected)

    with pytest.raises(RuntimeError, match=message):
        operation.correct_records(build_db(rows), apply=False)


def test_requires_both_confirmed_invoices() -> None:
    with pytest.raises(RuntimeError, match="exactamente los comprobantes confirmados"):
        operation.correct_records(build_db([build_row("0256-00046834")]), apply=False)
