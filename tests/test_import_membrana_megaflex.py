from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.bootstrap.import_membrana_megaflex import build_prices, normalize_invoice, parse_date, parse_decimal, upsert_precio


class FakeScalarDb:
    def __init__(self, existing=None) -> None:
        self.existing = existing
        self.added = None

    def scalar(self, _stmt):
        return self.existing

    def add(self, value) -> None:
        self.added = value


def test_membrana_parsers_normalizan_fecha_importe_y_comprobante() -> None:
    assert parse_date("14/03/2022") == date(2022, 3, 14)
    assert parse_decimal("$7.337,53") == Decimal("7337.53")
    assert normalize_invoice("ESTIMADO") == "ESTIMADO"
    assert normalize_invoice("253-04115") == "0253-00004115"


def test_build_prices_calcula_normalizado_sobre_20kg() -> None:
    prices = build_prices()

    assert len(prices) == 52
    first = prices[0]
    assert first.numero_comprobante == "ESTIMADO-2022-01-01"
    assert first.fecha == date(2022, 1, 1)
    assert first.precio_original == Decimal("8878.41")
    assert first.precio_normalizado == Decimal("443.9205")


def test_upsert_membrana_inserta_si_no_existe() -> None:
    price = build_prices()[0]
    db = FakeScalarDb()

    result = upsert_precio(
        db,
        precio=price,
        material=SimpleNamespace(id=10),
        presentacion=SimpleNamespace(id=11),
        fuente=SimpleNamespace(id=12),
    )

    assert result == "inserted"
    assert isinstance(db.added, PrecioHistorico)
    assert db.added.material_id == 10
    assert db.added.presentacion_id == 11
    assert db.added.fuente_id == 12
    assert db.added.numero_comprobante == "ESTIMADO-2022-01-01"
