from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.pricing.application import contextual_purchase_recommendations as contextual_module
from app.modules.pricing.application.contextual_purchase_recommendations import (
    ACCION_COMPRAR_AHORA,
    ACCION_ESCALONAR,
    ACCION_SIN_VENTAJA_CLARA,
    recomendar_estrategia_contextual,
    resolver_horizonte_contextual,
)
from app.modules.pricing.application.purchase_recommendations import PurchaseRecommendationResult
from app.modules.pricing.interfaces.dependencies import get_pricing_repository


def _base_recommendation(*, variacion: str = "8.0000", confiabilidad: str = "alta") -> PurchaseRecommendationResult:
    return PurchaseRecommendationResult(
        material_id=1,
        material_key="membrana-megaflex",
        horizonte_meses=3,
        decision="COMPRAR_AHORA",
        variacion_esperada_pct=Decimal(variacion),
        precio_actual=Decimal("100.00"),
        precio_proyectado_horizonte=Decimal("108.00"),
        cantidad_objetivo=Decimal("30"),
        impacto_economico_estimado=Decimal("240.00"),
        mape=Decimal("4.00"),
        umbral_decision_pct=Decimal("5.0000"),
        supera_umbral_decision=True,
        confiabilidad=confiabilidad,
        criticidad="alta",
        justificacion="Recomendacion base.",
        advertencias=(),
    )


def test_resolver_horizonte_desde_fecha_objetivo() -> None:
    assert (
        resolver_horizonte_contextual(
            horizonte_meses=None,
            fecha_objetivo_uso=date(2026, 8, 10),
            hoy=date(2026, 5, 26),
        )
        == 3
    )


def test_recomendacion_contextual_compra_ahora_por_fase_y_riesgo(monkeypatch) -> None:
    monkeypatch.setattr(contextual_module, "recomendar_momento_compra", lambda *_args, **_kwargs: _base_recommendation())

    result = recomendar_estrategia_contextual(
        SimpleNamespace(id=1, nombre="Membrana Megaflex"),
        fase_obra="impermeabilizacion",
        tolerancia_riesgo="baja",
        cantidad_objetivo=Decimal("30"),
        horizonte_meses=3,
        pricing_repo=object(),
    )

    assert result.decision == ACCION_COMPRAR_AHORA
    assert result.criticidad == "alta"
    assert result.umbral_decision_pct == Decimal("5.0000")
    assert "fase impermeabilizacion" in result.justificacion


def test_recomendacion_contextual_escalona_necesidad_critica_cercana(monkeypatch) -> None:
    monkeypatch.setattr(
        contextual_module,
        "recomendar_momento_compra",
        lambda *_args, **_kwargs: _base_recommendation(variacion="2.0000"),
    )

    result = recomendar_estrategia_contextual(
        SimpleNamespace(id=1, nombre="Cemento Portland"),
        fase_obra="estructura",
        tolerancia_riesgo="baja",
        cantidad_objetivo=Decimal("100"),
        horizonte_meses=2,
        pricing_repo=object(),
    )

    assert result.decision == ACCION_ESCALONAR
    assert result.supera_umbral_decision is False


def test_recomendacion_contextual_no_acciona_con_baja_confianza(monkeypatch) -> None:
    monkeypatch.setattr(
        contextual_module,
        "recomendar_momento_compra",
        lambda *_args, **_kwargs: _base_recommendation(confiabilidad="baja"),
    )

    result = recomendar_estrategia_contextual(
        SimpleNamespace(id=1, nombre="Pastina"),
        fase_obra="terminaciones",
        tolerancia_riesgo="media",
        cantidad_objetivo=Decimal("10"),
        horizonte_meses=6,
        pricing_repo=object(),
    )

    assert result.decision == ACCION_SIN_VENTAJA_CLARA


def test_endpoint_recomendacion_contextual_expone_contexto(monkeypatch) -> None:
    material = SimpleNamespace(id=1, nombre="Membrana Megaflex", unidad_base="unidad")
    monkeypatch.setattr(contextual_module, "recomendar_momento_compra", lambda *_args, **_kwargs: _base_recommendation())

    class FakeMaterialRepo:
        def get_by_id(self, material_id: int):
            return material if material_id == 1 else None

    app.dependency_overrides[get_material_repository] = lambda: FakeMaterialRepo()
    app.dependency_overrides[get_pricing_repository] = lambda: object()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).post(
            "/materiales/1/recomendacion-contextual",
            json={
                "fase_obra": "impermeabilizacion",
                "tolerancia_riesgo": "baja",
                "cantidad_objetivo": 30,
                "horizonte_meses": 3,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == ACCION_COMPRAR_AHORA
    assert body["fase_obra"] == "impermeabilizacion"
    assert body["tolerancia_riesgo"] == "baja"
    assert body["criticidad"] == "alta"
