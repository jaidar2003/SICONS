from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.modules.chat.application.commercial_assistant import (
    _optional_date,
    _optional_decimal,
    _optional_horizon,
    generar_propuesta_comercial,
    interpretar_necesidad_comercial,
)


def test_optional_decimal_invalid():
    with pytest.raises(ValueError, match="valor numerico invalido"):
        _optional_decimal("invalido")

def test_optional_date_invalid():
    assert _optional_date("invalido") is None

def test_optional_horizon_invalid():
    assert _optional_horizon("invalido") is None
    assert _optional_horizon(0) is None
    assert _optional_horizon(13) is None

def test_interpretar_necesidad_comercial_json_error():
    client = MagicMock()
    client.complete.return_value = "invalid json"
    with pytest.raises(HTTPException) as exc:
        interpretar_necesidad_comercial("hola", materials=[], client=client)
    assert exc.value.status_code == 502

def test_interpretar_necesidad_comercial_invalid_id():
    client = MagicMock()
    client.complete.return_value = '{"material_id": "no-soy-un-id"}'
    res = interpretar_necesidad_comercial("hola", materials=[], client=client)
    assert res.material_id is None

def test_interpretar_necesidad_comercial_decimal_error():
    client = MagicMock()
    client.complete.return_value = '{"cantidad": "invalido"}'
    with pytest.raises(HTTPException) as exc:
        interpretar_necesidad_comercial("hola", materials=[], client=client)
    assert exc.value.status_code == 502

def test_generar_propuesta_comercial_unsupported_material():
    material = MagicMock()
    material.nombre = "Material No Soportado"
    with pytest.raises(HTTPException) as exc:
        generar_propuesta_comercial(material=material, cantidad=Decimal("10"), fase_obra="general", tolerancia_riesgo="media", pricing_repo=None, db=None, client=None)
    assert exc.value.status_code == 422

def test_generar_propuesta_comercial_escalonar(monkeypatch):
    from app.modules.pricing.application.commercial_prices import CommercialPriceResult
    from app.modules.pricing.application.contextual_purchase_recommendations import (
        ContextualPurchaseRecommendationResult,
    )
    
    material = MagicMock(id=1, nombre="Cemento Portland")
    # Cemento Portland is in SUPPORTED_PRODUCT_KEYS
    
    price_res = CommercialPriceResult(
        material_id=1, material_key="cemento-portland", presentation_id=None, product_key="cemento-portland",
        costo_base_actual=Decimal("100"), costo_base_proyectado=Decimal("120"),
        margen_ganancia_pct=Decimal("0"), origen_margen="GLOBAL",
        precio_final_actual=Decimal("100"), precio_final_proyectado=Decimal("120"),
        ganancia_unitaria_actual=Decimal("0"), ganancia_unitaria_proyectada=Decimal("0"),
        advertencias=[]
    )
    
    recom_res = ContextualPurchaseRecommendationResult(
        material_id=1, material_key="cemento-portland", fase_obra="general",
        fecha_objetivo_uso=None, horizonte_meses=3, tolerancia_riesgo="media",
        criticidad="media", decision="COMPRAR_AHORA",
        variacion_esperada_pct=Decimal("20"), precio_actual=Decimal("100"),
        precio_proyectado_horizonte=Decimal("120"), precio_proyectado_optimista=Decimal("110"),
        precio_proyectado_pesimista=Decimal("130"), cantidad_objetivo=Decimal("10"),
        impacto_economico_estimado=Decimal("200"), mape=Decimal("5"),
        umbral_decision_pct=Decimal("5"), supera_umbral_decision=True,
        confiabilidad="alta", justificacion="test", advertencias=[]
    )
    
    monkeypatch.setattr("app.modules.chat.application.commercial_assistant.calcular_precio_comercial", lambda **k: price_res)
    monkeypatch.setattr("app.modules.chat.application.commercial_assistant.recomendar_estrategia_contextual", lambda *a, **k: recom_res)
    
    client = MagicMock()
    client.complete.return_value = "Propuesta generada"
    
    # presupuesto_maximo < total_actual (100 * 10 = 1000)
    res = generar_propuesta_comercial(
        material=material, cantidad=Decimal("10"), fase_obra="general", tolerancia_riesgo="media",
        pricing_repo=None, db=None, client=client, presupuesto_maximo=Decimal("500"), horizonte_meses=3
    )
    
    assert res.recomendacion.decision == "ESCALONAR"
    assert "supera el presupuesto maximo" in res.advertencias[-1]
