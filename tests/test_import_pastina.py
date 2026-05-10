from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.bootstrap.import_pastina import (
    grouped_prices,
    normalize_invoice,
    parse_date,
    parse_decimal,
    upsert_precio,
)


class FakeScalarDb:
    def __init__(self, existing=None) -> None:
        self.existing = existing
        self.added = None

    def scalar(self, _stmt):
        return self.existing

    def add(self, value) -> None:
        self.added = value


def test_proveedor_parsers_normalizan_fecha_importe_y_comprobante() -> None:
    assert parse_date("13/02/2026") == date(2026, 2, 13)
    assert parse_date("04-11-24") == date(2024, 11, 4)
    assert parse_decimal("$2.213,31") == Decimal("2213.31")
    assert normalize_invoice("ESTIMADO") == "ESTIMADO"
    assert normalize_invoice("63-16764") == "0063-00016764"
    assert normalize_invoice("0063-00003809") == "0063-00003809"


def test_grouped_prices_consolida_filas_por_factura() -> None:
    prices, skipped = grouped_prices()

    assert len(prices) == 51
    assert skipped == 0
    first = prices[0]
    assert first.numero_comprobante == "ESTIMADO-2022-01-01"
    assert first.fecha == date(2022, 1, 1)
    assert first.origen == "estimado"
    assert first.precio_sin_iva == Decimal("124.50")
    assert first.precio_original == Decimal("150.64")
    assert first.precio_normalizado == Decimal("150.6400")
    assert first.articulos == ("PASTINA KLAUKOL",)


def test_upsert_precio_inserta_si_no_existe() -> None:
    price = grouped_prices()[0][0]
    db = FakeScalarDb()

    result = upsert_precio(
        db,
        precio=price,
        material=SimpleNamespace(id=4),
        presentacion=SimpleNamespace(id=7),
        fuente=SimpleNamespace(id=9),
    )

    assert result == "inserted"
    assert isinstance(db.added, PrecioHistorico)
    assert db.added.material_id == 4
    assert db.added.presentacion_id == 7
    assert db.added.fuente_id == 9
    assert db.added.numero_comprobante == "ESTIMADO-2022-01-01"


def test_upsert_precio_no_cambia_registro_identico() -> None:
    price = grouped_prices()[0][0]
    existing = SimpleNamespace(
        material_id=4,
        presentacion_id=7,
        fecha=price.fecha,
        precio_original=price.precio_original,
        precio_normalizado=price.precio_normalizado,
        moneda="ARS",
        observaciones=(
            "Serie estimada Pastina SIKA 1 kg - SIKA - "
            "Px estimado s/IVA 124.50 - Articulos: PASTINA KLAUKOL"
        ),
    )
    db = FakeScalarDb(existing=existing)

    result = upsert_precio(
        db,
        precio=price,
        material=SimpleNamespace(id=4),
        presentacion=SimpleNamespace(id=7),
        fuente=SimpleNamespace(id=9),
    )

    assert result == "unchanged"
    assert db.added is None
