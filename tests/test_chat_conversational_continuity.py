from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.chat.application.interpretation import (
    ConversationState,
    advance_conversation_state,
    interpret_query,
    rebuild_conversation_state,
)
from app.modules.chat.infrastructure.models import ChatConversation
from app.modules.chat.interfaces import routes as chat_routes
from app.modules.chat.interfaces.routes import get_chat_client
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.database.session import get_db


class FakeClient:
    provider_name = "facultad"

    def complete(self, _messages):
        return "Respuesta explicada."


class FakeDb:
    def add(self, _entity):
        return None

    def flush(self):
        return None


def advance(state: ConversationState, text: str):
    interpretation = interpret_query(text, state)
    return interpretation, advance_conversation_state(state, interpretation)


def test_forecast_follow_ups_inherit_material_and_replace_horizon() -> None:
    state = rebuild_conversation_state(["Mostrame el cemento a tres meses."])

    interpretation, transition = advance(state, "¿Y a seis meses?")

    assert interpretation.intent.value == "FORECAST"
    assert interpretation.intent.origin == "inherited"
    assert interpretation.material.value == "cemento-portland"
    assert interpretation.material.origin == "inherited"
    assert transition.state.horizon_months == 6
    assert set(transition.inherited_fields) >= {"intent", "material"}


def test_material_change_keeps_comparison_horizon_but_clears_purchase_values() -> None:
    state = rebuild_conversation_state(
        [
            "Necesito 30 bolsas de cemento a 3 meses",
            "Tengo 200 mil pesos",
        ]
    )
    assert state.quantity == Decimal("30")
    assert state.budget == Decimal("200000")

    interpretation, transition = advance(state, "¿Y la pastina?")

    assert interpretation.intent.value == "PRESUPUESTO"
    assert transition.state.material_key == "pastina"
    assert transition.state.horizon_months == 3
    assert transition.state.quantity is None
    assert transition.state.budget is None
    assert transition.cleared_fields == ("quantity", "budget")


def test_budget_follow_up_inherits_quantity_for_same_material() -> None:
    state = rebuild_conversation_state(["Necesito 30 bolsas de cemento a 3 meses"])

    interpretation, transition = advance(state, "Tengo 200 mil pesos")

    assert interpretation.quantity.value == Decimal("30")
    assert interpretation.quantity.origin == "inherited"
    assert transition.state.budget == Decimal("200000")


def test_unrelated_help_does_not_erase_conversation_state() -> None:
    state = rebuild_conversation_state(["Mostrame la membrana a 6 meses", "¿Qué significa MAPE?"])

    assert state.material_key == "membrana-megaflex"
    assert state.horizon_months == 6
    assert state.intent == "FORECAST"


def test_http_follow_up_returns_editable_understanding(monkeypatch) -> None:
    conversation = ChatConversation(id=12, usuario_id=1, titulo="Seguimiento", material_actual_id=1, horizonte_actual=3)
    cement = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    monkeypatch.setattr(chat_routes, "_get_owned_conversation", lambda *_args: conversation)
    monkeypatch.setattr(chat_routes, "_recent_user_messages", lambda *_args: ["Mostrame el cemento a 3 meses"])
    monkeypatch.setattr(chat_routes, "_latest_assistant_message", lambda *_args: None)
    monkeypatch.setattr(chat_routes, "_persist_conversation_turn", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_routes, "_register_chat_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_routes, "_calculated_direct_answer", lambda **_kwargs: "La proyeccion fue calculada.")
    monkeypatch.setattr(
        chat_routes,
        "build_backend_retrieval_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            context="CONTEXTO CALCULADO",
            sources=("forecast_snapshots",),
            source_evidence=(),
            material=cement,
            material_resolution_source="contexto",
            horizon=6,
        ),
    )
    app.dependency_overrides[get_db] = lambda: FakeDb()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = FakeClient
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(
        get_by_id=lambda _material_id: cement,
        list_active=lambda: [cement],
    )
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "¿Y a 6 meses?", "conversation_id": 12},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["entendimiento"]["material"] == "Cemento Portland"
    assert body["entendimiento"]["horizon_months"] == 6
    assert set(body["entendimiento"]["inherited_fields"]) >= {"intent", "material"}
    assert body["sugerencias"] == ["Cambiar a 6 meses", "Explicar el MAPE", "Evaluar una compra"]
