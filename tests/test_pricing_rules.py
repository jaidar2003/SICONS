from decimal import Decimal

import pytest

from app.modules.pricing.domain import rules


def test_calcular_precio_normalizado_error():
    with pytest.raises(ValueError, match="mayor a cero"):
        rules.calcular_precio_normalizado(Decimal("100"), Decimal("0"))

def test_calcular_impacto_absoluto_error():
    with pytest.raises(ValueError, match="no puede ser negativa"):
        rules.calcular_impacto_absoluto(Decimal("100"), Decimal("110"), Decimal("-1"))

def test_calcular_variacion_esperada_porcentual_cero():
    assert rules.calcular_variacion_esperada_porcentual(Decimal("0"), Decimal("110")) == Decimal("0")

def test_normalizar_valores_vacio():
    assert rules.normalizar_valores([]) == []

def test_calcular_puntaje_criticidad_error():
    with pytest.raises(ValueError, match="no negativos"):
        rules.calcular_puntaje_criticidad(Decimal("1"), Decimal("1"), Decimal("-1"), Decimal("1"))
    with pytest.raises(ValueError, match="no negativos"):
        rules.calcular_puntaje_criticidad(Decimal("1"), Decimal("1"), Decimal("1"), Decimal("-1"))

def test_explicar_priorizacion_branches():
    # variacion_normalizada == impacto_normalizado
    assert "equilibrada" in rules.explicar_priorizacion(Decimal("0.5"), Decimal("0.5"), Decimal("10"), Decimal("100"))
    
    # impacto_normalizado > variacion_normalizada
    assert "impacto presupuestario" in rules.explicar_priorizacion(Decimal("0.4"), Decimal("0.6"), Decimal("10"), Decimal("100"))
    
    # variacion_normalizada > impacto_normalizado (the 'else' case)
    assert "mayor variacion esperada" in rules.explicar_priorizacion(Decimal("0.6"), Decimal("0.4"), Decimal("10"), Decimal("100"))
