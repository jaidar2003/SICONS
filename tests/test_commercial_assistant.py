from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.chat.application import commercial_assistant
from app.modules.chat.application.commercial_assistant import (
    generar_propuesta_comercial,
    interpretar_necesidad_comercial,
)
from app.modules.chat.interfaces.routes import get_chat_client
from app.modules.pricing.application.contextual_purchase_recommendations import ContextualPurchaseRecommendationResult
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.database.session import get_db


class FakeClient:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)


def test_interpretar_necesidad_usa_catalogo_mvp_y_campos_ia() -> None:
    client = FakeClient(
        """```json
        {"material_id": 3, "producto_nombre": "Membrana Megaflex", "cantidad": 30,
         "fase_obra": "impermeabilizacion", "fecha_objetivo_uso": "2026-09-15",
         "horizonte_meses": null, "presupuesto_maximo": 1800000,
         "tolerancia_riesgo": "baja", "datos_faltantes": []}
        ```"""
    )
    materials = [
        SimpleNamespace(id=1, nombre="Cemento Portland"),
        SimpleNamespace(id=3, nombre="Membrana Megaflex"),
        SimpleNamespace(id=8, nombre="Ladrillo"),
    ]

    result = interpretar_necesidad_comercial("Necesito impermeabilizar en septiembre", materials=materials, client=client)

    assert result.material_id == 3
    assert result.producto_nombre == "Membrana Megaflex"
    assert result.cantidad == Decimal("30")
    assert result.datos_faltantes == ()
    assert "Ladrillo" not in client.calls[0][0]["content"]


def test_interpretar_necesidad_marca_producto_fuera_del_mvp_y_faltantes() -> None:
    client = FakeClient(
        '{"material_id": 8, "producto_nombre": "Ladrillo", "cantidad": null, "fase_obra": null, '
        '"fecha_objetivo_uso": null, "horizonte_meses": null, "presupuesto_maximo": null, '
        '"tolerancia_riesgo": "media", "datos_faltantes": ["cantidad"]}'
    )

    result = interpretar_necesidad_comercial(
        "Necesito ladrillos",
        materials=[SimpleNamespace(id=8, nombre="Ladrillo")],
        client=client,
    )

    assert result.material_id is None
    assert set(result.datos_faltantes) == {"producto", "cantidad", "fase_obra", "fecha_objetivo_uso_o_horizonte_meses"}


def test_generar_propuesta_usa_precio_comercial_y_recomendacion_calculada(monkeypatch) -> None:
    monkeypatch.setattr(
        commercial_assistant,
        "calcular_precio_comercial",
        lambda **_kwargs: SimpleNamespace(
            precio_final_actual=Decimal("120.00"),
            precio_final_proyectado=Decimal("138.00"),
            advertencias=(),
        ),
    )
    recommendation = SimpleNamespace(
        decision="COMPRAR_AHORA",
        confiabilidad="alta",
        mape=Decimal("4.00"),
        justificacion="La suba supera el umbral.",
        advertencias=(),
    )
    monkeypatch.setattr(commercial_assistant, "recomendar_estrategia_contextual", lambda *_args, **_kwargs: recommendation)
    client = FakeClient("Conviene comprar ahora según el presupuesto calculado.")

    result = generar_propuesta_comercial(
        material=SimpleNamespace(id=3, nombre="Membrana Megaflex"),
        cantidad=Decimal("30"),
        fase_obra="impermeabilizacion",
        tolerancia_riesgo="baja",
        horizonte_meses=3,
        pricing_repo=object(),
        db=object(),
        client=client,
    )

    assert result.total_actual == Decimal("3600.00")
    assert result.total_proyectado == Decimal("4140.00")
    assert result.diferencia_estimada == Decimal("540.00")
    assert result.recomendacion.decision == "COMPRAR_AHORA"
    assert '"total_actual": "3600.00"' in client.calls[0][0]["content"]
    assert result.fuente_decision == "backend_deterministico"
    assert result.propuesta_generada_por == "llm_validado"


def test_generar_propuesta_reemplaza_redaccion_llm_si_inventa_valores(monkeypatch) -> None:
    monkeypatch.setattr(
        commercial_assistant,
        "calcular_precio_comercial",
        lambda **_kwargs: SimpleNamespace(
            precio_final_actual=Decimal("120.00"),
            precio_final_proyectado=Decimal("138.00"),
            advertencias=(),
        ),
    )
    recommendation = SimpleNamespace(
        decision="COMPRAR_AHORA",
        confiabilidad="alta",
        mape=Decimal("4.00"),
        justificacion="La suba supera el umbral.",
        advertencias=(),
    )
    monkeypatch.setattr(commercial_assistant, "recomendar_estrategia_contextual", lambda *_args, **_kwargs: recommendation)
    client = FakeClient("Conviene postergar porque el total sera 9999.")

    result = generar_propuesta_comercial(
        material=SimpleNamespace(id=3, nombre="Membrana Megaflex"),
        cantidad=Decimal("30"),
        fase_obra="impermeabilizacion",
        tolerancia_riesgo="baja",
        horizonte_meses=3,
        pricing_repo=object(),
        db=object(),
        client=client,
    )

    assert result.recomendacion.decision == "COMPRAR_AHORA"
    assert result.propuesta_generada_por == "backend_deterministico"
    assert "9999" not in result.propuesta
    assert "COMPRAR_AHORA" in result.propuesta
    assert result.advertencias == ("La redaccion generativa fue reemplazada por una explicacion deterministica del backend.",)


def test_generar_propuesta_escalona_si_presupuesto_no_cubre_compra_inmediata(monkeypatch) -> None:
    monkeypatch.setattr(
        commercial_assistant,
        "calcular_precio_comercial",
        lambda **_kwargs: SimpleNamespace(
            precio_final_actual=Decimal("120.00"),
            precio_final_proyectado=Decimal("138.00"),
            advertencias=(),
        ),
    )
    recommendation = ContextualPurchaseRecommendationResult(
        material_id=3,
        material_key="membrana-megaflex",
        fase_obra="impermeabilizacion",
        fecha_objetivo_uso=None,
        horizonte_meses=3,
        tolerancia_riesgo="baja",
        criticidad="alta",
        decision="COMPRAR_AHORA",
        variacion_esperada_pct=Decimal("15.00"),
        precio_actual=Decimal("100.00"),
        precio_proyectado_horizonte=Decimal("115.00"),
        precio_proyectado_optimista=None,
        precio_proyectado_pesimista=None,
        cantidad_objetivo=Decimal("30"),
        impacto_economico_estimado=Decimal("450.00"),
        umbral_decision_pct=Decimal("5.00"),
        supera_umbral_decision=True,
        confiabilidad="alta",
        mape=Decimal("4.00"),
        justificacion="Comprar ahora.",
        advertencias=(),
    )
    monkeypatch.setattr(commercial_assistant, "recomendar_estrategia_contextual", lambda *_args, **_kwargs: recommendation)

    result = generar_propuesta_comercial(
        material=SimpleNamespace(id=3, nombre="Membrana Megaflex"),
        cantidad=Decimal("30"),
        fase_obra="impermeabilizacion",
        tolerancia_riesgo="baja",
        horizonte_meses=3,
        presupuesto_maximo=Decimal("1800.00"),
        pricing_repo=object(),
        db=object(),
        client=FakeClient("Comprar por etapas."),
    )

    assert result.recomendacion.decision == "ESCALONAR"
    assert "15.0000 unidades" in result.recomendacion.justificacion
    assert result.advertencias == ("La compra inmediata completa supera el presupuesto maximo informado.",)


def test_endpoints_presupuestacion_interpretan_y_generan_propuesta(monkeypatch) -> None:
    material = SimpleNamespace(id=3, nombre="Membrana Megaflex")
    client = FakeClient(
        '{"material_id": 3, "producto_nombre": "Membrana Megaflex", "cantidad": 30, '
        '"fase_obra": "impermeabilizacion", "fecha_objetivo_uso": null, "horizonte_meses": 3, '
        '"presupuesto_maximo": null, "tolerancia_riesgo": "baja", "datos_faltantes": []}'
    )
    monkeypatch.setattr(
        "app.modules.chat.interfaces.routes.generar_propuesta_comercial",
        lambda **_kwargs: SimpleNamespace(
            material_id=3,
            producto_nombre="Membrana Megaflex",
            cantidad=Decimal("30"),
            fase_obra="impermeabilizacion",
            fecha_objetivo_uso=None,
            horizonte_meses=3,
            tolerancia_riesgo="baja",
            presupuesto_maximo=None,
            precio_unitario_actual=Decimal("120.00"),
            total_actual=Decimal("3600.00"),
            precio_unitario_proyectado=Decimal("138.00"),
            total_proyectado=Decimal("4140.00"),
            diferencia_estimada=Decimal("540.00"),
            recomendacion=SimpleNamespace(
                decision="COMPRAR_AHORA",
                confiabilidad="alta",
                mape=Decimal("4.00"),
                justificacion="Comprar ahora.",
            ),
            propuesta="Propuesta lista.",
            advertencias=(),
        ),
    )
    material_repo = SimpleNamespace(list_active=lambda: [material], get_by_id=lambda _id: material)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: client
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = lambda: object()
    app.dependency_overrides[get_db] = lambda: object()
    try:
        interpretation = TestClient(app).post(
            "/chat/presupuestacion/interpretar",
            json={"necesidad": "Necesito 30 membranas dentro de tres meses"},
        )
        proposal = TestClient(app).post(
            "/chat/presupuestacion/propuesta",
            json={
                "material_id": 3,
                "cantidad": 30,
                "fase_obra": "impermeabilizacion",
                "tolerancia_riesgo": "baja",
                "horizonte_meses": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert interpretation.status_code == 200
    assert interpretation.json()["material_id"] == 3
    assert interpretation.json()["requiere_validacion"] is True
    assert interpretation.json()["requiere_confirmacion"] is True
    assert proposal.status_code == 200
    assert proposal.json()["total_actual"] == "3600.00"
    assert proposal.json()["decision"] == "COMPRAR_AHORA"
