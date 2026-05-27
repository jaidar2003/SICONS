from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.modules.pricing.application.priorities import (
    MaterialPriorityInput,
    priorizar_materiales_criticos,
    priorizar_materiales_desde_forecast,
)
from app.modules.pricing.domain.exceptions import MaterialNotFoundException
from app.modules.pricing.domain.rules import (
    calcular_impacto_absoluto,
    calcular_variacion_esperada_porcentual,
    etiquetar_criticidad,
    normalizar_valores,
)
from app.modules.pricing.interfaces.schemas import (
    MaterialCriticidadCreate,
    MaterialCriticidadItemCreate,
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


def test_priorizar_materiales_criticos_empty() -> None:
    assert priorizar_materiales_criticos([]) == []


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


def test_priorizar_materiales_desde_forecast(monkeypatch) -> None:
    mock_material_repo = MagicMock()
    mock_pricing_repo = MagicMock()
    
    material = MagicMock()
    material.id = 1
    material.nombre = "Cemento"
    material.unidad_base = "kg"
    mock_material_repo.get_by_id.return_value = material
    
    mock_forecast = MagicMock()
    mock_forecast.dataset = [MagicMock(y=100.0)]
    mock_forecast.forecast = [MagicMock(precio_proyectado=Decimal("110.00"))]
    
    monkeypatch.setattr("app.modules.pricing.application.priorities.forecast_material", lambda *args: mock_forecast)
    
    payload = MaterialCriticidadCreate(
        horizonte_meses=3,
        materiales=[MaterialCriticidadItemCreate(material_id=1, cantidad_requerida=Decimal("50"))]
    )
    
    result = priorizar_materiales_desde_forecast(payload, mock_material_repo, mock_pricing_repo)
    
    assert result.horizonte_meses == 3
    assert len(result.materiales) == 1
    assert result.materiales[0].material_id == 1
    assert result.materiales[0].precio_proyectado_normalizado == Decimal("110.00")


def test_priorizar_materiales_desde_forecast_material_not_found() -> None:
    mock_material_repo = MagicMock()
    mock_material_repo.get_by_id.return_value = None
    
    payload = MaterialCriticidadCreate(
        materiales=[MaterialCriticidadItemCreate(material_id=999, cantidad_requerida=Decimal("50"))]
    )
    
    with pytest.raises(MaterialNotFoundException):
        priorizar_materiales_desde_forecast(payload, mock_material_repo, MagicMock())
