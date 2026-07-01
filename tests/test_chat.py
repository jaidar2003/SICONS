from datetime import date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.chat.application.context import build_material_context, resolve_horizon
from app.modules.chat.application.operations import execute_operation, plan_operation
from app.modules.chat.application.retrieval import (
    build_backend_retrieval_context,
    classify_chat_intent,
    suggest_visualization,
)
from app.modules.chat.application import retrieval as chat_retrieval
from app.modules.chat.application.service import ADMIN_ONLY_RESPONSE, OUT_OF_SCOPE_RESPONSE, answer_question
from app.modules.chat.infrastructure import llm_client
from app.modules.chat.infrastructure.llm_client import (
    AnthropicChatClient,
    FallbackChatClient,
    LLMConfigurationError,
    OpenAICompatibleChatClient,
)
from app.modules.chat.infrastructure.models import ChatConversation, ChatMessage
from app.modules.chat.interfaces import routes as chat_routes
from app.modules.chat.interfaces.routes import (
    _persist_conversation_turn,
    _semantic_question_for_conversation,
    get_chat_client,
)
from app.modules.chat.interfaces.schemas import ChatResponseRead
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.database.session import get_db


class FakeChatClient:
    def __init__(self, response: str = "Respuesta basada en BuildWise.") -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []
        self.provider_name = "facultad"

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.response


class ResponseQueueClient:
    def __init__(self, *responses: str) -> None:
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []
        self.provider_name = "facultad"

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)


class FakeDb:
    def __init__(self):
        self.added = []

    def add(self, _entity):
        self.added.append(_entity)
        return None

    def commit(self):
        return None

    def flush(self):
        return None

    def refresh(self, entity):
        return entity

    def rollback(self):
        return None

    def scalar(self, _stmt):
        return 2

    def scalars(self, _stmt):
        return []

    def execute(self, _stmt):
        return []


def test_consulta_fuera_de_alcance_no_invoca_proveedor() -> None:
    client = FakeChatClient()

    result = answer_question("Pasame una receta de flan", client)

    assert result.aceptada is False
    assert result.proveedor_utilizado is False
    assert result.respuesta == OUT_OF_SCOPE_RESPONSE
    assert client.calls == []


def test_consulta_buildwise_invoca_proveedor_con_prompt_restringido() -> None:
    client = FakeChatClient()

    result = answer_question("Que significa la confiabilidad del forecast de cemento?", client)

    assert result.aceptada is True
    assert result.proveedor_utilizado is True
    assert "BuildWise" in client.calls[0][0]["content"]
    assert "alertas, notificaciones" in client.calls[0][0]["content"]
    assert client.calls[0][1]["content"] == "Que significa la confiabilidad del forecast de cemento?"


def test_consulta_con_contexto_acepta_seguimiento_y_envia_historial() -> None:
    client = FakeChatClient()

    result = answer_question(
        "Explicate eso que me decis",
        client,
        context="CONTEXTO CALCULADO POR BUILDWISE.\n- Decision del motor: COMPRAR_AHORA.",
        history=[{"role": "assistant", "content": "Conviene comprar ahora."}],
    )

    assert result.aceptada is True
    assert "Decision del motor: COMPRAR_AHORA" in client.calls[0][0]["content"]
    assert client.calls[0][1] == {"role": "assistant", "content": "Conviene comprar ahora."}
    assert client.calls[0][2]["content"] == "Explicate eso que me decis"


def test_persist_conversation_turn_guarda_mensajes_y_estado_rag() -> None:
    db = FakeDb()
    conversation = ChatConversation(id=7, usuario_id=1, titulo="Forecast cemento")
    response = ChatResponseRead(
        aceptada=True,
        respuesta="Respuesta persistida.",
        proveedor_utilizado=True,
        proveedor_ia="facultad",
        tipo_intencion="FORECAST",
        contexto_usado=True,
        fuentes_recuperadas=["purchase_recommendations"],
        material_resuelto_id=1,
        material_resuelto="Cemento Portland",
        horizonte_resuelto=12,
        conversation_id=7,
    )

    _persist_conversation_turn(db, conversation=conversation, question="Ahora a 12 meses", response=response)

    assert [message.role for message in db.added] == ["user", "assistant"]
    assert db.added[0].content == "Ahora a 12 meses"
    assert db.added[1].content == "Respuesta persistida."
    assert db.added[1].tipo_intencion == "FORECAST"
    assert conversation.material_actual_id == 1
    assert conversation.horizonte_actual == 12


def test_listar_mensajes_conversacion_aplica_paginacion_y_orden_desc(monkeypatch: pytest.MonkeyPatch) -> None:
    class CapturingDb(FakeDb):
        def scalars(self, stmt):
            self.stmt = stmt
            return [
                ChatMessage(
                    id=11,
                    conversation_id=7,
                    role="user",
                    content="Mensaje paginado",
                    created_at=datetime(2026, 6, 5, 10, 0, 0),
                )
            ]

    db = CapturingDb()
    monkeypatch.setattr(chat_routes, "_get_owned_conversation", lambda *_args: SimpleNamespace(id=7))

    result = chat_routes.listar_mensajes_conversacion(
        7,
        limit=2,
        offset=4,
        order="desc",
        db=db,
        current_user=SimpleNamespace(id=1),
    )

    sql = str(db.stmt.compile(compile_kwargs={"literal_binds": True}))
    assert result[0].content == "Mensaje paginado"
    assert "ORDER BY chat_messages.created_at DESC, chat_messages.id DESC" in sql
    assert "LIMIT 2" in sql
    assert "OFFSET 4" in sql


def test_semantic_question_hereda_forecast_en_followup_visual() -> None:
    latest = ChatMessage(
        role="assistant",
        content="Forecast calculado.",
        visualizacion_sugerida={"tipo": "FORECAST", "material_id": 1, "horizonte_meses": 6},
    )

    assert _semantic_question_for_conversation("Ahora mostrame a 12 meses", latest) == "Ahora mostrame a 12 meses forecast"


@pytest.mark.parametrize(
    ("previous_intent", "expected_suffix"),
    [("FORECAST", "forecast"), ("RECOMENDACION", "recomendacion")],
)
def test_semantic_question_hereda_intencion_en_followup_de_horizonte(
    previous_intent: str,
    expected_suffix: str,
) -> None:
    latest = SimpleNamespace(tipo_intencion=previous_intent, visualizacion_sugerida=None)

    assert _semantic_question_for_conversation("y a 6 meses?", latest) == f"y a 6 meses? {expected_suffix}"


def test_resolve_horizon_prioriza_meses_escritos_en_pregunta() -> None:
    assert resolve_horizon("Necesito cemento dentro de 6 meses", 3) == 6
    assert resolve_horizon("Necesito cemento dentro de 24 meses", 3) == 3


def test_build_material_context_formatea_recomendacion_real(monkeypatch: pytest.MonkeyPatch) -> None:
    recommendation = SimpleNamespace(
        horizonte_meses=6,
        decision="COMPRAR_AHORA",
        confiabilidad="media",
        justificacion="El precio proyectado sube.",
        precio_actual=100,
        precio_proyectado_horizonte=130,
        precio_proyectado_optimista=120,
        precio_proyectado_pesimista=140,
        variacion_esperada_pct=30,
        mape=5,
        advertencias=(),
    )
    monkeypatch.setattr(
        "app.modules.chat.application.context.recomendar_momento_compra",
        lambda *_args, **_kwargs: recommendation,
    )

    context = build_material_context(SimpleNamespace(nombre="Cemento Portland", unidad_base="kg"), 6, object())

    assert "Cemento Portland" in context
    assert "COMPRAR_AHORA" in context
    assert "ARS 100 por kg" in context
    assert "No pidas precios por zona" in context
    assert "operaciones administrativas" not in context


def test_build_material_context_informa_operaciones_administrativas_solo_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    recommendation = SimpleNamespace(
        horizonte_meses=3,
        decision="MONITOREAR",
        confiabilidad="media",
        justificacion="Revisar.",
        precio_actual=None,
        precio_proyectado_horizonte=None,
        precio_proyectado_optimista=None,
        precio_proyectado_pesimista=None,
        variacion_esperada_pct=None,
        mape=None,
        advertencias=(),
    )
    monkeypatch.setattr(
        "app.modules.chat.application.context.recomendar_momento_compra",
        lambda *_args, **_kwargs: recommendation,
    )

    context = build_material_context(SimpleNamespace(nombre="Cemento Portland", unidad_base="kg"), 3, object(), is_admin=True)

    assert "operaciones administrativas" in context


def test_backend_retrieval_resuelve_material_por_nombre_y_usa_historicos() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    prices = [
        SimpleNamespace(
            id=1,
            fecha=date(2026, 1, 1),
            precio_normalizado=100,
            fuente=SimpleNamespace(nombre="Factura compra"),
            numero_comprobante="A-1",
        ),
        SimpleNamespace(
            id=2,
            fecha=date(2026, 2, 1),
            precio_normalizado=120,
            fuente=SimpleNamespace(nombre="Factura compra"),
            numero_comprobante="A-2",
        ),
    ]
    material_repo = SimpleNamespace(list_active=lambda: [material], get_by_id=lambda _id: material)
    pricing_repo = SimpleNamespace(get_historical_prices=lambda _material_id, _since: prices)

    result = build_backend_retrieval_context(
        "Cual fue el ultimo precio de cemento?",
        material_repo=material_repo,
        pricing_repo=pricing_repo,
        db=FakeDb(),
    )

    assert result.material == material
    assert "FUENTE precios_historicos" in result.context
    assert "Ultimo precio normalizado: ARS 120" in result.context
    assert result.sources == ("catalogo.materiales", "precios_historicos")
    assert result.source_evidence == (
        {
            "source": "precios_historicos",
            "records": [
                {
                    "fecha": "2026-02-01",
                    "precio_normalizado": "120",
                    "unidad_base": "kg",
                    "fuente": "Factura compra",
                    "comprobante": "A-2",
                },
                {
                    "fecha": "2026-01-01",
                    "precio_normalizado": "100",
                    "unidad_base": "kg",
                    "fuente": "Factura compra",
                    "comprobante": "A-1",
                },
            ],
        },
    )


def test_backend_retrieval_margenes_no_admin_no_expone_detalle() -> None:
    result = build_backend_retrieval_context(
        "Mostrame los margenes comerciales",
        material_repo=SimpleNamespace(list_active=lambda: []),
        pricing_repo=object(),
        db=FakeDb(),
        is_admin=False,
    )

    assert "solo para usuarios administradores" in result.context


def test_backend_retrieval_resuelve_alias_de_materiales() -> None:
    cemento = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    pastina = SimpleNamespace(id=2, nombre="Pastina", unidad_base="kg")
    membrana = SimpleNamespace(id=3, nombre="Membrana Megaflex", unidad_base="unidad")
    material_repo = SimpleNamespace(list_active=lambda: [cemento, pastina, membrana], get_by_id=lambda _id: None)

    assert build_backend_retrieval_context(
        "Cuanto sale klaukol?",
        material_repo=material_repo,
        pricing_repo=SimpleNamespace(get_historical_prices=lambda *_args: []),
        db=FakeDb(),
    ).material == pastina
    assert build_backend_retrieval_context(
        "Necesito membrana asfaltica",
        material_repo=material_repo,
        pricing_repo=SimpleNamespace(get_historical_prices=lambda *_args: []),
        db=FakeDb(),
    ).material == membrana
    assert build_backend_retrieval_context(
        "Precio de cemnto en 3 meses",
        material_repo=material_repo,
        pricing_repo=SimpleNamespace(get_historical_prices=lambda *_args: []),
        db=FakeDb(),
    ).material == cemento


def test_suggest_visualization_historico_usa_material_y_no_modelo() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland")

    result = suggest_visualization(
        "Mostrame la evolucion del precio de cemento",
        intent="HISTORICO",
        material=material,
        horizon=3,
    )

    assert result == {"tipo": "PRICE_HISTORY", "material_id": 1, "horizonte_meses": None}


def test_suggest_visualization_forecast_incluye_horizonte() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland")

    result = suggest_visualization(
        "Graficame el forecast de cemento a 6 meses",
        intent="FORECAST",
        material=material,
        horizon=6,
    )

    assert result == {"tipo": "FORECAST", "material_id": 1, "horizonte_meses": 6}


def test_suggest_visualization_sin_pedido_visual_no_sugiere_grafico() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland")

    assert suggest_visualization("Cual fue el ultimo precio?", intent="HISTORICO", material=material, horizon=3) is None


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("cual fue el ultimo precio de cemento?", "HISTORICO"),
        ("explicame el forecast de cemento", "FORECAST"),
        ("me conviene comprar cemento?", "RECOMENDACION"),
        ("necesito comprar 500 kg de cemento", "PRESUPUESTO"),
        ("que materiales hay?", "CATALOGO"),
        ("lista usuarios", "ADMIN"),
    ],
)
def test_classify_chat_intent(question: str, expected: str) -> None:
    assert classify_chat_intent(question) == expected
    assert classify_chat_intent("receta de flan", accepted_scope=False) == "FUERA_ALCANCE"


def test_plan_operation_extrae_accion_estructurada() -> None:
    client = FakeChatClient('{"action":"COMPARE_STRATEGIES","material_id":1,"cantidad":100,"horizonte_meses":6}')
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    result = plan_operation(
        "Compara estrategias para 100 kg de cemento en 6 meses",
        client,
        materials=[material],
        selected_material_id=1,
        horizon=3,
    )

    assert result["action"] == "COMPARE_STRATEGIES"
    assert result["cantidad"] == 100


def test_plan_operation_comparacion_comun_no_invoca_ia() -> None:
    client = FakeChatClient('{"action":"NONE"}')
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    result = plan_operation(
        "Compara estrategias para 100 kg de cemento en 6 meses",
        client,
        materials=[material],
        selected_material_id=None,
        horizon=6,
    )

    assert result["action"] == "COMPARE_STRATEGIES"
    assert result["material_id"] == 1
    assert result["cantidad"] == Decimal("100")
    assert client.calls == []


def test_plan_operation_cliente_descarta_accion_admin() -> None:
    client = FakeChatClient('{"action":"LIST_USERS"}')
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    result = plan_operation(
        "Lista usuarios",
        client,
        materials=[material],
        selected_material_id=1,
        horizon=3,
        allow_admin=False,
    )

    assert result["action"] == "NONE"
    assert "LIST_USERS" not in client.calls[0][0]["content"]


def test_execute_operation_compara_estrategias_calculadas(monkeypatch: pytest.MonkeyPatch) -> None:
    result = SimpleNamespace(
        horizonte_meses=6,
        precio_actual=100,
        precio_proyectado_horizonte=120,
        variacion_esperada_pct=20,
        mejor_estrategia="COMPRAR_AHORA",
        ahorro_estimado=2000,
        confiabilidad="alta",
    )
    monkeypatch.setattr(
        "app.modules.chat.application.operations.comparar_estrategias_compra",
        lambda *_args, **_kwargs: result,
    )
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    operation = execute_operation(
        {"action": "COMPARE_STRATEGIES", "material_id": 1, "cantidad": 100, "horizonte_meses": 6},
        fallback_material=material,
        fallback_horizon=3,
        material_repo=SimpleNamespace(get_by_id=lambda _id: material),
        pricing_repo=object(),
    )

    assert operation.action == "COMPARE_STRATEGIES"
    assert "Mejor estrategia: COMPRAR_AHORA" in operation.context
    assert "ARS 2000" in operation.context


def test_execute_operation_administrativa_requiere_confirmacion() -> None:
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")

    operation = execute_operation(
        {"action": "CREATE_PRICE", "material_id": 1, "precio": 300, "fecha": "2026-05-20"},
        fallback_material=material,
        fallback_horizon=3,
        material_repo=SimpleNamespace(get_by_id=lambda _id: material),
        pricing_repo=object(),
        db=object(),
        current_user=SimpleNamespace(id=1, rol="admin"),
        confirmed=False,
    )

    assert "PENDIENTE DE CONFIRMACION" in operation.context
    assert "No se modifico ningun dato" in operation.context


def test_openai_compatible_client_usa_base_url_configurada(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs) -> httpx.Response:
        captured["url"] = url
        captured["kwargs"] = kwargs
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Respuesta remota"}}]}, request=request)

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    client = OpenAICompatibleChatClient(
        base_url="https://ai.cloud.um.edu.ar/api/v1/",
        api_key="token",
        model="gemma4-26b",
        timeout_seconds=12,
    )

    response = client.complete([{"role": "user", "content": "Consulta"}])

    assert response == "Respuesta remota"
    assert captured["url"] == "https://ai.cloud.um.edu.ar/api/v1/chat/completions"
    kwargs = captured["kwargs"]
    assert kwargs["headers"]["Authorization"] == "Bearer token"
    assert kwargs["json"]["model"] == "gemma4-26b"
    assert kwargs["timeout"] == 12


def test_openai_compatible_client_requiere_configuracion() -> None:
    client = OpenAICompatibleChatClient(base_url="", api_key="", model="")

    with pytest.raises(LLMConfigurationError):
        client.complete([{"role": "user", "content": "Consulta"}])


def test_anthropic_client_usa_messages_y_headers_nativos(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, **kwargs) -> httpx.Response:
        captured["url"] = url
        captured["kwargs"] = kwargs
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Respuesta Claude"}]}, request=request)

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    client = AnthropicChatClient(
        base_url="https://api.anthropic.com/v1/",
        api_key="claude-token",
        model="claude-sonnet-test",
        api_version="2023-06-01",
        max_tokens=512,
        timeout_seconds=12,
    )

    response = client.complete(
        [
            {"role": "system", "content": "Solo BuildWise."},
            {"role": "user", "content": "Consulta"},
        ]
    )

    assert response == "Respuesta Claude"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    kwargs = captured["kwargs"]
    assert kwargs["headers"]["x-api-key"] == "claude-token"
    assert kwargs["headers"]["anthropic-version"] == "2023-06-01"
    assert kwargs["json"]["system"] == "Solo BuildWise."
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "Consulta"}]
    assert kwargs["json"]["max_tokens"] == 512


def test_provider_anthropic_selecciona_cliente_nativo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_routes.settings, "openai_base_url", "https://facultad.example/api/v1")
    monkeypatch.setattr(chat_routes.settings, "openai_api_key", "openai-token")
    monkeypatch.setattr(chat_routes.settings, "openai_model", "facultad-modelo")
    monkeypatch.setattr(chat_routes.settings, "anthropic_base_url", "https://api.anthropic.com/v1")
    monkeypatch.setattr(chat_routes.settings, "anthropic_api_key", "claude-token")
    monkeypatch.setattr(chat_routes.settings, "anthropic_model", "claude-sonnet")
    monkeypatch.setattr(
        chat_routes,
        "_read_persisted_chat_config",
        lambda _db=None: {
            "proveedor_activo": "claude",
            "modelo_facultad": "facultad-modelo",
            "modelo_claude": "claude-sonnet",
        },
    )

    client = get_chat_client()

    assert isinstance(client, FallbackChatClient)
    assert isinstance(client.primary, AnthropicChatClient)
    assert isinstance(client.fallback, OpenAICompatibleChatClient)


def test_respuestas_directas_cubren_precio_catalogo_y_forecast(monkeypatch: pytest.MonkeyPatch) -> None:
    price_answer = chat_routes._latest_price_answer(
        question="ultimo precio bolsa de 50 kg cemento",
        material_name="Cemento Portland",
        source_evidence=[
            {
                "source": "precios_historicos",
                "records": [
                    {
                        "precio_normalizado": "123.45",
                        "unidad_base": "kg",
                        "fecha": "2026-03-25",
                        "fuente": "Factura compra",
                    }
                ],
            }
        ],
    )
    assert "bolsa de 5E+1 kg" in price_answer
    assert "ARS 6172.50" in price_answer

    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    db = MagicMock()
    db.scalars.return_value = [
        SimpleNamespace(nombre_presentacion="Bolsa 25 kg", cantidad_base=Decimal("25"), unidad_presentacion="kg")
    ]
    catalog_answer = chat_routes._catalog_direct_answer(
        question="que presentaciones tiene cemento",
        material=material,
        material_repo=MagicMock(),
        db=db,
    )
    assert "unidad base: kg" in catalog_answer
    assert "Bolsa 25 kg" in catalog_answer

    forecast_result = SimpleNamespace(
        dataset=[SimpleNamespace(ds=date(2026, 3, 1), y=100.0)],
        forecast=[SimpleNamespace(fecha=date(2026, 6, 1), precio_proyectado=Decimal("110.00"))],
        metricas=SimpleNamespace(mape=Decimal("4.22")),
        seleccion_modelo=SimpleNamespace(confiabilidad="alta"),
    )
    monkeypatch.setattr(chat_routes, "forecast_material", lambda *args, **kwargs: forecast_result)
    forecast_answer = chat_routes._calculated_direct_answer(
        question="forecast de cemento",
        intent="FORECAST",
        material=material,
        horizon=3,
        pricing_repo=object(),
    )
    assert "Forecast de Cemento Portland" in forecast_answer
    assert "MAPE: 4.22%" in forecast_answer


def test_contextos_rag_cubren_catalogo_indices_fuentes_y_margenes() -> None:
    material = SimpleNamespace(
        id=1,
        nombre="Cemento Portland",
        unidad_base="kg",
        categoria="Construccion",
        marca="Loma Negra",
        descripcion="Cemento de uso general",
    )
    presentation = SimpleNamespace(
        id=7,
        material_id=1,
        nombre_presentacion="Bolsa 50 kg",
        cantidad_base=Decimal("50"),
        unidad_presentacion="kg",
    )
    source = SimpleNamespace(id=3, nombre="Factura compra", tipo_fuente="factura")
    margin = SimpleNamespace(
        id=9,
        scope="GLOBAL",
        material_id=None,
        presentation_id=None,
        margen_ganancia_pct=Decimal("12.5"),
    )

    db = MagicMock()
    db.scalars.side_effect = [[presentation], [presentation], [source], [], [margin]]
    db.execute.return_value = [("INDEC", "ipim_nivel_general", 51, date(2022, 1, 1), date(2026, 3, 1))]

    catalog_lines = chat_retrieval._catalog_context([material] * 9, db)
    assert any("Materiales activos disponibles: 9" in line for line in catalog_lines)
    assert any("materiales activos adicionales" in line for line in catalog_lines)
    assert any("Bolsa 50 kg" in line for line in catalog_lines)

    material_lines = chat_retrieval._material_catalog_context(material, db)
    assert any("Categoria: Construccion" in line for line in material_lines)
    assert any("Marca: Loma Negra" in line for line in material_lines)
    assert any("Descripcion: Cemento de uso general" in line for line in material_lines)

    index_lines = chat_retrieval._external_indices_context(db)
    assert index_lines == ["FUENTE external_index_values:", "- INDEC/ipim_nivel_general: 51 registros; rango 2022-01-01 a 2026-03-01."]

    source_lines = chat_retrieval._sources_context(db)
    assert source_lines == ["FUENTE catalogo.fuentes:", "- ID 3: Factura compra; tipo factura."]

    no_margin_lines = chat_retrieval._margins_context(db, 1, is_admin=False)
    assert "solo para usuarios administradores" in no_margin_lines[1]

    admin_empty_lines = chat_retrieval._margins_context(db, 1, is_admin=True)
    assert "No hay margenes comerciales activos" in admin_empty_lines[1]

    admin_margin_lines = chat_retrieval._margins_context(db, None, is_admin=True)
    assert "margen 12.5%" in admin_margin_lines[1]


def test_rag_cubre_ramas_sin_datos_visualizacion_y_recomendacion(monkeypatch: pytest.MonkeyPatch) -> None:
    assert suggest_visualization("mostrame el forecast", intent="FORECAST", material=SimpleNamespace(), horizon=3) is None
    combined_visualization = suggest_visualization(
        "mostrame historico y forecast de cemento",
        intent="FORECAST",
        material=SimpleNamespace(id=1),
        horizon=6,
    )
    assert combined_visualization == {"tipo": "PRICE_HISTORY_FORECAST", "material_id": 1, "horizonte_meses": 6}

    selected_material = SimpleNamespace(id=2, nombre="Pastina", unidad_base="kg")
    material_repo = MagicMock()
    material_repo.list_active.return_value = [SimpleNamespace(id=99, nombre="", unidad_base="kg")]
    material_repo.get_by_id.return_value = selected_material
    resolved, source = chat_retrieval.resolve_material_from_question_with_source(
        "sin material explicito",
        material_repo,
        selected_material_id=2,
    )
    assert resolved is selected_material
    assert source == "contexto"

    assert chat_retrieval._source_priority(SimpleNamespace(fuente=None)) == 1
    assert chat_retrieval._source_priority(SimpleNamespace(fuente=SimpleNamespace(nombre="Canonico"))) == 0

    db = MagicMock()
    db.execute.return_value = []
    db.scalars.return_value = []
    assert "No hay indices externos" in chat_retrieval._external_indices_context(db)[1]
    assert "No hay fuentes registradas" in chat_retrieval._sources_context(db)[1]

    empty_context = build_backend_retrieval_context(
        "fuentes indices margenes",
        material_repo=material_repo,
        pricing_repo=MagicMock(),
        db=db,
        is_admin=True,
    )
    assert empty_context.context is not None
    assert "external_index_values" in empty_context.sources
    assert "catalogo.fuentes" in empty_context.sources
    assert "commercial_margins" in empty_context.sources

    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    recommendation = SimpleNamespace(
        decision="COMPRAR_AHORA",
        confiabilidad="alta",
        justificacion="El precio proyectado sube.",
        precio_actual=Decimal("100.00"),
        precio_proyectado_horizonte=Decimal("120.00"),
        variacion_esperada_pct=Decimal("20.00"),
    )
    monkeypatch.setattr(chat_routes, "recomendar_momento_compra", lambda *args, **kwargs: recommendation)
    answer = chat_routes._calculated_direct_answer(
        question="conviene comprar cemento",
        intent="RECOMENDACION",
        material=material,
        horizon=3,
        pricing_repo=object(),
    )
    assert "Decision para Cemento Portland" in answer
    assert "Variacion esperada: 20.00%" in answer


def test_admin_puede_leer_configuracion_de_ia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_routes.settings, "chat_provider", "openai")
    monkeypatch.setattr(chat_routes.settings, "openai_model", "facultad-modelo")
    monkeypatch.setattr(chat_routes.settings, "anthropic_model", "claude-modelo")
    monkeypatch.setattr(chat_routes.settings, "openai_base_url", "https://facultad.example/api/v1")
    monkeypatch.setattr(chat_routes.settings, "openai_api_key", "openai-token")
    monkeypatch.setattr(chat_routes.settings, "anthropic_base_url", "https://api.anthropic.com/v1")
    monkeypatch.setattr(chat_routes.settings, "anthropic_api_key", "claude-token")
    monkeypatch.setattr(chat_routes, "_read_persisted_chat_config", lambda _db=None: chat_routes._chat_config_from_settings())

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).get("/chat/config")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "proveedor_activo": "facultad",
        "modelo_facultad": "facultad-modelo",
        "modelo_claude": "claude-modelo",
        "fallback_habilitado": True,
    }


def test_admin_puede_actualizar_configuracion_de_ia(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_routes.settings, "chat_provider", "openai")
    monkeypatch.setattr(chat_routes.settings, "openai_model", "facultad-modelo")
    monkeypatch.setattr(chat_routes.settings, "anthropic_model", "claude-modelo")
    monkeypatch.setattr(chat_routes.settings, "openai_base_url", "https://facultad.example/api/v1")
    monkeypatch.setattr(chat_routes.settings, "openai_api_key", "openai-token")
    monkeypatch.setattr(chat_routes.settings, "anthropic_base_url", "https://api.anthropic.com/v1")
    monkeypatch.setattr(chat_routes.settings, "anthropic_api_key", "claude-token")

    stored_config = SimpleNamespace(
        proveedor_activo="facultad",
        modelo_facultad="facultad-modelo",
        modelo_claude="claude-modelo",
    )
    fake_db = FakeDb()
    fake_db.get = lambda *_args: stored_config
    monkeypatch.setattr(
        chat_routes,
        "_read_persisted_chat_config",
        lambda _db=None: {
            "proveedor_activo": stored_config.proveedor_activo,
            "modelo_facultad": stored_config.modelo_facultad,
            "modelo_claude": stored_config.modelo_claude,
        },
    )

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    app.dependency_overrides[get_db] = lambda: fake_db
    try:
        response = TestClient(app).patch(
            "/chat/config",
            json={
                "proveedor_activo": "claude",
                "modelo_facultad": "facultad-nueva",
                "modelo_claude": "claude-nuevo",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "proveedor_activo": "claude",
        "modelo_facultad": "facultad-nueva",
        "modelo_claude": "claude-nuevo",
        "fallback_habilitado": True,
    }
    assert chat_routes.settings.chat_provider == "anthropic"
    assert chat_routes.settings.openai_model == "facultad-nueva"
    assert chat_routes.settings.anthropic_model == "claude-nuevo"


def test_endpoint_chat_rechaza_fuera_de_alcance_sin_proveedor() -> None:
    provider = FakeChatClient()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "Dame una receta de flan"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["aceptada"] is False
    assert response.json()["proveedor_utilizado"] is False
    assert provider.calls == []


def test_endpoint_chat_precio_historico_directo_no_invoca_ia() -> None:
    provider = FakeChatClient()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    prices = [
        SimpleNamespace(
            id=1,
            fecha=date(2026, 3, 25),
            precio_normalizado=Decimal("196.6115"),
            fuente=SimpleNamespace(nombre="Factura compra"),
            numero_comprobante="FC-1",
        ),
        SimpleNamespace(
            id=2,
            fecha=date.today() + timedelta(days=30),
            precio_normalizado=Decimal("999.0000"),
            fuente=SimpleNamespace(nombre="Dato futuro"),
            numero_comprobante="FUT-1",
        ),
    ]
    material_repo = SimpleNamespace(get_by_id=lambda _id: None, list_active=lambda: [material])
    pricing_repo = SimpleNamespace(get_historical_prices=lambda *_args: prices)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = lambda: pricing_repo
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "cual es el precio del cemento"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["proveedor_utilizado"] is False
    assert body["proveedor_ia"] is None
    assert body["tipo_intencion"] == "HISTORICO"
    assert body["horizonte_resuelto"] is None
    assert "ARS 196.6115 por kg" in body["respuesta"]
    assert "999.0000" not in body["respuesta"]
    assert provider.calls == []


def test_endpoint_chat_admite_seguimiento_de_unidad_con_material_de_conversacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeChatClient()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    conversation = SimpleNamespace(id=7, usuario_id=1, material_actual_id=1, horizonte_actual=3)

    monkeypatch.setattr(chat_routes, "_get_owned_conversation", lambda *_args: conversation)
    monkeypatch.setattr(chat_routes, "_latest_assistant_message", lambda *_args: None)
    monkeypatch.setattr(chat_routes, "_conversation_history", lambda *_args: [])
    monkeypatch.setattr(chat_routes, "_persist_conversation_turn", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(chat_routes, "_register_chat_audit", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        chat_routes,
        "build_backend_retrieval_context",
        lambda *_args, **_kwargs: SimpleNamespace(
            context="CONTEXTO RECUPERADO DE BUILDWISE",
            sources=("catalogo.materiales",),
            source_evidence=(),
            material=material,
            material_resolution_source="contexto",
            horizon=3,
        ),
    )
    monkeypatch.setattr(chat_routes, "_catalog_direct_answer", lambda **_kwargs: "Cemento Portland usa como unidad base: kg.")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(
        get_by_id=lambda _id: material,
        list_active=lambda: [material],
    )
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "y cual es su unidad base?", "conversation_id": 7},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["aceptada"] is True
    assert response.json()["tipo_intencion"] == "CATALOGO"
    assert response.json()["material_resuelto"] == "Cemento Portland"
    assert response.json()["material_resolution_source"] == "contexto"
    assert provider.calls == []


def test_endpoint_chat_precio_bolsa_25kg_multiplica_precio_normalizado() -> None:
    provider = FakeChatClient()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    prices = [
        SimpleNamespace(
            id=1,
            fecha=date(2026, 3, 25),
            precio_normalizado=Decimal("196.6115"),
            fuente=SimpleNamespace(nombre="Factura compra"),
            numero_comprobante="FC-1",
        )
    ]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: None, list_active=lambda: [material])
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace(get_historical_prices=lambda *_args: prices)
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "cual es el precio de la bolsa de 25kg de cemento"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["proveedor_utilizado"] is False
    assert body["horizonte_resuelto"] is None
    assert "bolsa de 25 kg" in body["respuesta"]
    assert "ARS 4915.29" in body["respuesta"]
    assert provider.calls == []


def test_endpoint_chat_bolsa_de_cemento_sin_kg_asume_25kg() -> None:
    provider = FakeChatClient()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    prices = [
        SimpleNamespace(
            id=1,
            fecha=date(2026, 3, 25),
            precio_normalizado=Decimal("196.6115"),
            fuente=SimpleNamespace(nombre="Factura compra"),
            numero_comprobante="FC-1",
        )
    ]
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: None, list_active=lambda: [material])
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace(get_historical_prices=lambda *_args: prices)
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "cual es el precio de la bolsa de cemento"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["proveedor_utilizado"] is False
    assert body["horizonte_resuelto"] is None
    assert "bolsa de 25 kg" in body["respuesta"]
    assert "ARS 4915.29" in body["respuesta"]
    assert provider.calls == []


def test_endpoint_chat_catalogo_materiales_responde_sin_ia() -> None:
    provider = FakeChatClient()
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: None, list_active=lambda: [material])
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace(get_historical_prices=lambda *_args: [])
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "que materiales hay?"})
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["proveedor_utilizado"] is False
    assert body["tipo_intencion"] == "CATALOGO"
    assert "Cemento Portland (kg)" in body["respuesta"]
    assert provider.calls == []


def test_endpoint_chat_llama_proveedor_para_consulta_admitida(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeChatClient(response="El forecast expresa una proyeccion del sistema.")
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    material_repo = SimpleNamespace(get_by_id=lambda _material_id: None, list_active=lambda: [material])
    monkeypatch.setattr(chat_routes, "build_material_context", lambda _material, horizon, _repo, **_kwargs: f"CONTEXTO {horizon} meses")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = object
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Explicame el forecast de Cemento Portland"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "aceptada": True,
        "respuesta": "El forecast expresa una proyeccion del sistema.",
        "proveedor_utilizado": True,
        "proveedor_ia": "facultad",
        "fallback_usado": False,
        "tipo_intencion": "FORECAST",
        "contexto_usado": True,
        "fuentes_recuperadas": ["catalogo.materiales", "purchase_recommendations"],
        "fuentes_evidencia": [],
        "material_resuelto_id": 1,
        "material_resuelto": "Cemento Portland",
        "material_resolution_source": "pregunta",
        "horizonte_resuelto": 3,
        "visualizacion_sugerida": None,
        "conversation_id": None,
    }
    assert len(provider.calls) == 1


def test_endpoint_chat_registra_auditoria(monkeypatch: pytest.MonkeyPatch) -> None:
    audit_calls = []

    def fake_register_audit_log(_db, **kwargs):
        audit_calls.append(kwargs)

    provider = FakeChatClient(response="Respuesta auditada.")
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    monkeypatch.setattr(chat_routes, "register_audit_log", fake_register_audit_log)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=11, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(list_active=lambda: [material], get_by_id=lambda _id: None)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": "Que materiales hay?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert audit_calls
    audit = audit_calls[0]
    assert audit["usuario_id"] == 11
    assert audit["accion"] == "CHAT_QUERY"
    assert audit["recurso"] == "ChatConsulta"
    assert audit["cambios"]["pregunta"] == "Que materiales hay?"
    assert audit["cambios"]["tipo_intencion"] == "CATALOGO"
    assert "duration_ms" in audit["cambios"]


def test_endpoint_chat_incluye_contexto_calculado_del_material(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeChatClient(response="Segun BuildWise, conviene comprar ahora.")
    material_repo = SimpleNamespace(get_by_id=lambda _material_id: SimpleNamespace(nombre="Cemento Portland", unidad_base="kg"))
    monkeypatch.setattr(chat_routes, "build_material_context", lambda _material, horizon, _repo, **_kwargs: f"CONTEXTO {horizon} meses")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = object
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={
                "pregunta": "Me conviene comprar cemento en 6 meses?",
                "material_id": 1,
                "horizonte_meses": 3,
                "historial": [{"role": "assistant", "content": "Respuesta previa"}],
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "CONTEXTO 6 meses" in provider.calls[0][0]["content"]
    assert provider.calls[0][1] == {"role": "assistant", "content": "Respuesta previa"}
    assert response.json()["contexto_usado"] is True
    assert response.json()["tipo_intencion"] == "RECOMENDACION"
    assert "purchase_recommendations" in response.json()["fuentes_recuperadas"]
    assert response.json()["material_resuelto"] == "Cemento Portland"
    assert response.json()["horizonte_resuelto"] == 6


def test_endpoint_chat_sugiere_visualizacion_desde_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeChatClient(response="Te muestro el forecast calculado por BuildWise.")
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg", categoria=None, marca=None, descripcion=None)
    material_repo = SimpleNamespace(get_by_id=lambda _material_id: None, list_active=lambda: [material])
    monkeypatch.setattr(chat_routes, "build_material_context", lambda _material, horizon, _repo, **_kwargs: f"CONTEXTO {horizon} meses")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = object
    app.dependency_overrides[get_db] = lambda: FakeDb()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Graficame el forecast de Cemento Portland a 6 meses"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["visualizacion_sugerida"] == {
        "tipo": "FORECAST",
        "material_id": 1,
        "horizonte_meses": 6,
    }


def test_endpoint_chat_ejecuta_operacion_analitica_planificada(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = ResponseQueueClient(
        '{"action":"COMPARE_STRATEGIES","material_id":1,"cantidad":100,"horizonte_meses":6}',
        "La estrategia calculada es comprar ahora.",
    )
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    material_repo = SimpleNamespace(get_by_id=lambda _material_id: material, list_active=lambda: [material])
    monkeypatch.setattr(chat_routes, "build_material_context", lambda *_args: "CONTEXTO BASE")
    monkeypatch.setattr(
        chat_routes,
        "execute_operation",
        lambda *_args, **_kwargs: SimpleNamespace(context="RESULTADO REAL DE ESTRATEGIAS"),
    )
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_material_repository] = lambda: material_repo
    app.dependency_overrides[get_pricing_repository] = object
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Compara estrategias para cemento en 6 meses y 100 kg", "material_id": 1},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(provider.calls) == 1
    assert "RESULTADO REAL DE ESTRATEGIAS" in provider.calls[0][0]["content"]
    assert response.json()["material_resuelto"] == "Cemento Portland"
    assert response.json()["horizonte_resuelto"] == 6


@pytest.mark.parametrize(
    "question",
    [
        "Lista los usuarios registrados",
        "Carga un precio historico para cemento",
        "Actualizar margen comercial del cemento",
    ],
)
def test_endpoint_chat_cliente_rechaza_acciones_admin_sin_proveedor(question: str) -> None:
    provider = FakeChatClient()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    try:
        response = TestClient(app).post("/chat/consultas", json={"pregunta": question})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "aceptada": False,
        "respuesta": ADMIN_ONLY_RESPONSE,
        "proveedor_utilizado": False,
        "proveedor_ia": None,
        "fallback_usado": False,
        "tipo_intencion": "ADMIN",
        "contexto_usado": False,
        "fuentes_recuperadas": [],
        "fuentes_evidencia": [],
        "material_resuelto_id": None,
        "material_resuelto": None,
        "material_resolution_source": None,
        "horizonte_resuelto": None,
        "visualizacion_sugerida": None,
        "conversation_id": None,
    }
    assert provider.calls == []


def test_endpoint_chat_admin_only_conversation_persiste_turno(monkeypatch: pytest.MonkeyPatch) -> None:
    db = FakeDb()
    conversation = SimpleNamespace(id=7, usuario_id=2, material_actual_id=None, horizonte_actual=None)
    monkeypatch.setattr(chat_routes, "_get_owned_conversation", lambda *_args: conversation)
    monkeypatch.setattr(chat_routes, "_latest_assistant_message", lambda *_args: None)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: None, list_active=lambda: [])
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Lista los usuarios registrados", "conversation_id": 7},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    persisted_messages = [entity for entity in db.added if isinstance(entity, ChatMessage)]
    assert [entity.role for entity in persisted_messages] == ["user", "assistant"]
    assert persisted_messages[1].content == ADMIN_ONLY_RESPONSE


def test_endpoint_chat_reusa_horizonte_persistido_en_seguimiento(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeChatClient(response="El forecast sigue la conversación previa.")
    db = FakeDb()
    conversation = SimpleNamespace(id=7, usuario_id=1, material_actual_id=1, horizonte_actual=12)
    material = SimpleNamespace(id=1, nombre="Cemento Portland", unidad_base="kg")
    captured = {}

    def fake_build_backend_retrieval_context(_question, **kwargs):
        captured["fallback_horizon"] = kwargs["fallback_horizon"]
        return SimpleNamespace(
            context=f"CTX {kwargs['fallback_horizon']}",
            sources=[],
            source_evidence=[],
            material=material,
            horizon=kwargs["fallback_horizon"],
        )

    monkeypatch.setattr(chat_routes, "_get_owned_conversation", lambda *_args: conversation)
    monkeypatch.setattr(chat_routes, "_latest_assistant_message", lambda *_args: None)
    monkeypatch.setattr(chat_routes, "build_backend_retrieval_context", fake_build_backend_retrieval_context)
    monkeypatch.setattr(chat_routes, "build_material_context", lambda _material, horizon, _repo, **_kwargs: f"CTX {horizon}")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="cliente")
    app.dependency_overrides[get_chat_client] = lambda: provider
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: material, list_active=lambda: [material])
    app.dependency_overrides[get_pricing_repository] = lambda: SimpleNamespace()
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Ahora mostrame eso", "conversation_id": 7, "material_id": 1},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["fallback_horizon"] == 12
    assert "CTX 12" in provider.calls[0][0]["content"]
    assert response.json()["horizonte_resuelto"] == 12

def test_consultar_chat_admin_only_request_denied_for_regular_user():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Listar usuarios", "historial": []},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["aceptada"] is False
    assert "administrador" in data["respuesta"]

def test_consultar_chat_llm_config_error(monkeypatch):
    from app.modules.chat.infrastructure.llm_client import LLMConfigurationError
    def mock_answer(*args, **kwargs):
        raise LLMConfigurationError("IA no configurada")
    monkeypatch.setattr("app.modules.chat.interfaces.routes.answer_question", mock_answer)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Hola", "historial": []},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert "configurada" in response.json()["detail"]

def test_consultar_chat_llm_provider_error(monkeypatch):
    from app.modules.chat.infrastructure.llm_client import LLMProviderError
    def mock_answer(*args, **kwargs):
        raise LLMProviderError("error provider")
    monkeypatch.setattr("app.modules.chat.interfaces.routes.answer_question", mock_answer)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Hola", "historial": []},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert "error provider" in response.json()["detail"]

def test_consultar_chat_with_operation_plan(monkeypatch):
    monkeypatch.setattr("app.modules.chat.interfaces.routes.needs_operation_plan", lambda x: True)
    monkeypatch.setattr("app.modules.chat.interfaces.routes.plan_operation", lambda *args, **kwargs: {"action": "LIST_USERS"})
    
    from app.modules.chat.application.operations import OperationResult
    monkeypatch.setattr("app.modules.chat.interfaces.routes.execute_operation", 
                        lambda *args, **kwargs: OperationResult(context="LISTA DE USUARIOS", action="LIST_USERS"))
    
    from app.modules.chat.application.service import ChatAnswer
    monkeypatch.setattr("app.modules.chat.interfaces.routes.answer_question", 
                        lambda *args, **kwargs: ChatAnswer(aceptada=True, respuesta="Aqui estan los usuarios", proveedor_utilizado=True))
    
    mock_db = MagicMock()
    mock_db.scalars.return_value = iter([])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(id=1), list_active=lambda: [])
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Lista los usuarios", "historial": [], "material_id": 1},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert "usuarios" in response.json()["respuesta"]

def test_consultar_chat_operation_plan_value_error(monkeypatch):
    monkeypatch.setattr("app.modules.chat.interfaces.routes.needs_operation_plan", lambda x: True)
    monkeypatch.setattr("app.modules.chat.interfaces.routes.plan_operation", lambda *args, **kwargs: {"action": "LIST_USERS"})
    
    def mock_execute(*args, **kwargs):
        raise ValueError("falta un dato")
    monkeypatch.setattr("app.modules.chat.interfaces.routes.execute_operation", mock_execute)
    
    from app.modules.chat.application.service import ChatAnswer
    monkeypatch.setattr("app.modules.chat.interfaces.routes.answer_question", 
                        lambda *args, **kwargs: ChatAnswer(aceptada=True, respuesta="Error controlado", proveedor_utilizado=True))
    
    mock_db = MagicMock()
    mock_db.scalars.return_value = iter([])
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    app.dependency_overrides[get_material_repository] = lambda: SimpleNamespace(get_by_id=lambda _id: SimpleNamespace(id=1), list_active=lambda: [])
    try:
        response = TestClient(app).post(
            "/chat/consultas",
            json={"pregunta": "Lista los usuarios", "historial": [], "material_id": 1},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200


def test_admin_puede_listar_auditoria_chat() -> None:
    audit_row = SimpleNamespace(
        id=99,
        usuario_id=11,
        accion="CHAT_QUERY",
        recurso="ChatConsulta",
        cambios={
            "pregunta": "cual fue el ultimo precio de cemento?",
            "respuesta": "Respuesta trazable.",
            "aceptada": True,
            "tipo_intencion": "HISTORICO",
            "contexto_usado": True,
            "fuentes_recuperadas": ["precios_historicos"],
            "material_resuelto": "Cemento Portland",
            "horizonte_resuelto": 3,
            "proveedor_ia": "facultad",
            "fallback_usado": False,
            "duration_ms": 123,
        },
        ip_address="127.0.0.1",
        created_at="2026-06-03T10:00:00",
    )
    db = SimpleNamespace(execute=lambda _stmt: SimpleNamespace(all=lambda: [(audit_row, "cliente")]))
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).get("/chat/auditoria?tipo_intencion=HISTORICO&fallback_usado=false")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body[0]["username"] == "cliente"
    assert body[0]["tipo_intencion"] == "HISTORICO"
    assert body[0]["material_resuelto"] == "Cemento Portland"
    assert body[0]["duration_ms"] == 123


def test_cliente_no_puede_listar_auditoria_chat() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    try:
        response = TestClient(app).get("/chat/auditoria")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_puede_medir_determinismo_rag() -> None:
    def row(row_id, cambios):
        return SimpleNamespace(id=row_id, cambios=cambios, usuario_id=11, ip_address=None, created_at="2026-06-03T10:00:00")

    logs = [
        row(
            1,
            {
                "pregunta": "Cual fue el ultimo precio de cemento?",
                "tipo_intencion": "HISTORICO",
                "material_resuelto": "Cemento Portland",
                "horizonte_resuelto": 3,
                "fuentes_recuperadas": ["precios_historicos", "catalogo.materiales"],
                "contexto_usado": True,
                "fallback_usado": False,
            },
        ),
        row(
            2,
            {
                "pregunta": "cual fue el ultimo precio de cemento",
                "tipo_intencion": "HISTORICO",
                "material_resuelto": "Cemento Portland",
                "horizonte_resuelto": 3,
                "fuentes_recuperadas": ["catalogo.materiales", "precios_historicos"],
                "contexto_usado": True,
                "fallback_usado": False,
            },
        ),
        row(
            3,
            {
                "pregunta": "Que materiales hay?",
                "tipo_intencion": "CATALOGO",
                "material_resuelto": None,
                "horizonte_resuelto": 3,
                "fuentes_recuperadas": ["catalogo.materiales"],
                "contexto_usado": True,
                "fallback_usado": False,
            },
        ),
    ]
    db = SimpleNamespace(scalars=lambda _stmt: logs)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).get("/chat/auditoria/determinismo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_consultas"] == 3
    assert body["grupos_repetidos"] == 1
    assert body["consultas_evaluadas"] == 2
    assert body["score_promedio"] == 1
    assert body["grupos"][0]["campos_variables"] == []


def test_cliente_no_puede_medir_determinismo_rag() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    try:
        response = TestClient(app).get("/chat/auditoria/determinismo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_admin_puede_ver_metricas_agregadas_de_auditoria() -> None:
    logs = [
        SimpleNamespace(
            cambios={
                "pregunta": "Cual fue el ultimo precio de cemento?",
                "tipo_intencion": "HISTORICO",
                "fallback_usado": False,
                "duration_ms": 100,
            },
            usuario_id=11,
        ),
        SimpleNamespace(
            cambios={
                "pregunta": "Explicame el forecast de cemento",
                "tipo_intencion": "FORECAST",
                "fallback_usado": True,
                "duration_ms": 200,
            },
            usuario_id=12,
        ),
        SimpleNamespace(
            cambios={
                "pregunta": "Dame una receta de flan",
                "tipo_intencion": "FUERA_ALCANCE",
                "fallback_usado": False,
                "duration_ms": 400,
            },
            usuario_id=12,
        ),
    ]
    db = SimpleNamespace(scalars=lambda _stmt: logs)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).get("/chat/auditoria/metricas")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_consultas"] == 3
    assert body["consultas_fuera_de_alcance"] == 1
    assert body["tasa_fallback"] == pytest.approx(1 / 3, rel=1e-4)
    assert body["latencia_promedio_ms"] == pytest.approx(233.33, rel=1e-3)
    assert body["latencia_p95_ms"] == 400.0
    assert body["consultas_por_intencion"]["FORECAST"] == 1
    assert body["usuarios_unicos"] == 2


def test_admin_puede_ver_bateria_canonica() -> None:
    logs = [
        SimpleNamespace(
            cambios={
                "pregunta": "cual fue el ultimo precio de cemento?",
                "tipo_intencion": "HISTORICO",
                "material_resuelto": "Cemento Portland",
                "horizonte_resuelto": None,
                "fuentes_recuperadas": ["catalogo.materiales", "precios_historicos"],
            },
            usuario_id=11,
        ),
        SimpleNamespace(
            cambios={
                "pregunta": "explicame el forecast de cemento",
                "tipo_intencion": "FORECAST",
                "material_resuelto": "Cemento Portland",
                "horizonte_resuelto": 3,
                "fuentes_recuperadas": ["purchase_recommendations"],
            },
            usuario_id=11,
        ),
    ]
    db = SimpleNamespace(scalars=lambda _stmt: logs)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, rol="admin")
    try:
        response = TestClient(app).get("/chat/auditoria/determinismo/canonicas")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["total_casos"] >= 1
    assert body["casos_con_evidencia"] == 2
    assert body["casos"][0]["pregunta"] == "cual fue el ultimo precio de cemento?"
    assert body["casos"][0]["cumple_expectativa"] is True
    assert body["casos"][0]["score"] == 1


def test_cliente_no_puede_ver_metricas_ni_bateria_canonica() -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=2, rol="cliente")
    try:
        metrics = TestClient(app).get("/chat/auditoria/metricas")
        canonical = TestClient(app).get("/chat/auditoria/determinismo/canonicas")
    finally:
        app.dependency_overrides.clear()

    assert metrics.status_code == 403
    assert canonical.status_code == 403
