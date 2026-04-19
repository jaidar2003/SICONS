from decimal import Decimal

import pytest

from app.services.pricing import calcular_precio_normalizado


def test_calcular_precio_normalizado() -> None:
    resultado = calcular_precio_normalizado(Decimal("12500.00"), Decimal("50.0000"))

    assert resultado == Decimal("250")


def test_calcular_precio_normalizado_rechaza_cantidad_cero() -> None:
    with pytest.raises(ValueError):
        calcular_precio_normalizado(Decimal("12500.00"), Decimal("0"))
