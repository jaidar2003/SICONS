from decimal import Decimal

import pytest

from app.modules.pricing.application.priorities import (
    MaterialPriorityInput,
    priorizar_materiales_criticos,
)
from app.modules.pricing.domain.rules import (
    calcular_impacto_absoluto,
    calcular_variacion_esperada_porcentual,
    etiquetar_criticidad,
    normalizar_valores,
)


def _material(
    material_id: int,
    nombre: str,
    cantidad: str,
    precio_actual: str,
    precio_proyectado: str,
) -> MaterialPriorityInput:
    return MaterialPriorityInput(
        material_id=material_id,
        material_nombre=nombre,
        unidad_base="kg",
        cantidad_requerida=Decimal(cantidad),
        precio_actual_normalizado=Decimal(precio_actual),
        precio_proyectado_normalizado=Decimal(precio_proyectado),
    )


def test_calcular_impacto_absoluto() -> None:
    impacto = calcular_impacto_absoluto(Decimal("100.00"), Decimal("112.00"), Decimal("50"))
    assert impacto == Decimal("600.0000")


def test_calcular_variacion_esperada_porcentual() -> None:
    variacion = calcular_variacion_esperada_porcentual(Decimal("100.00"), Decimal("112.00"))
    assert variacion == Decimal("12.0000")


def test_normalizar_valores_evta_division_por_cero() -> None:
    normalizados = normalizar_valores([Decimal("0"), Decimal("0")])
    assert normalizados == [Decimal("0"), Decimal("0")]


def test_etiquetar_criticidad() -> None:
    assert etiquetar_criticidad(Decimal("0.80")) == "alta"
    assert etiquetar_criticidad(Decimal("0.50")) == "media"
    assert etiquetar_criticidad(Decimal("0.10")) == "baja"


def test_priorizar_materiales_ordena_por_criticidad() -> None:
    ranking = priorizar_materiales_criticos(
        [
            _material(1, "Cemento", "100", "100.00", "112.00"),
            _material(2, "Arena", "100", "100.00", "104.00"),
            _material(3, "Hierro", "100", "100.00", "125.00"),
        ]
    )

    assert [item.material_nombre for item in ranking] == ["Hierro", "Cemento", "Arena"]


def test_priorizar_materiales_asigna_etiquetas_y_explicacion() -> None:
    ranking = priorizar_materiales_criticos(
        [
            _material(1, "Cemento", "100", "100.00", "100.00"),
            _material(2, "Hierro", "100", "100.00", "130.00"),
        ]
    )

    assert ranking[0].nivel_criticidad == "alta"
    assert "Priorizado" in ranking[0].explicacion
    assert ranking[-1].nivel_criticidad == "baja"
    assert ranking[-1].explicacion == "Sin aumento proyectado relevante en el horizonte analizado."


def test_priorizar_materiales_maneja_variacion_cero_e_impacto_cero() -> None:
    ranking = priorizar_materiales_criticos([_material(1, "Cemento", "100", "100.00", "100.00")])
    assert ranking[0].criticidad == Decimal("0.0000")
    assert ranking[0].impacto_absoluto == Decimal("0.0000")
    assert ranking[0].variacion_esperada_porcentual == Decimal("0.0000")


def test_priorizar_materiales_rechaza_pesos_invalidos() -> None:
    with pytest.raises(ValueError, match="no pueden ser ambos cero"):
        priorizar_materiales_criticos([_material(1, "Cemento", "100", "100.00", "120.00")], alpha=Decimal("0"), beta=Decimal("0"))
