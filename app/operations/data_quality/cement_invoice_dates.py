from __future__ import annotations

from datetime import date

CONFIRMED_INVOICE_DATES = {
    "0256-00046834": date(2025, 11, 26),
    "0256-00046835": date(2025, 11, 26),
}


def normalize_confirmed_invoice_date(numero_comprobante: str, observed_date: date) -> date:
    """Apply corrections confirmed against the original purchase documents."""
    return CONFIRMED_INVOICE_DATES.get(numero_comprobante, observed_date)
