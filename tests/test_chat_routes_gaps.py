from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.chat.infrastructure.llm_client import FallbackChatClient, LLMConfigurationError, LLMProviderError
from app.modules.chat.interfaces.routes import AnthropicChatClient, get_chat_client
from app.shared.config.settings import settings


def test_get_chat_client_anthropic(monkeypatch):
    monkeypatch.setattr(
        "app.modules.chat.interfaces.routes._read_persisted_chat_config",
        lambda _db=None: {
            "proveedor_activo": "claude",
            "modelo_facultad": settings.openai_model,
            "modelo_claude": settings.anthropic_model,
        },
    )
    client = get_chat_client()
    assert isinstance(client, FallbackChatClient)
    assert isinstance(client.primary, AnthropicChatClient)


def test_get_chat_client_default_usa_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.modules.chat.interfaces.routes._read_persisted_chat_config",
        lambda _db=None: {
            "proveedor_activo": "facultad",
            "modelo_facultad": settings.openai_model,
            "modelo_claude": settings.anthropic_model,
        },
    )
    client = get_chat_client()
    assert isinstance(client, FallbackChatClient)

def test_interpretar_necesidad_llm_errors(monkeypatch):
    monkeypatch.setattr("app.modules.chat.interfaces.routes.interpretar_necesidad_comercial", MagicMock(side_effect=LLMConfigurationError("config error")))
    mock_repo = MagicMock()
    mock_repo.list_active.return_value = []
    app.dependency_overrides[get_current_user] = lambda: MagicMock(id=1, rol="cliente")
    app.dependency_overrides[get_material_repository] = lambda: mock_repo
    client = TestClient(app)
    response = client.post("/chat/presupuestacion/interpretar", json={"necesidad": "hola"})
    assert response.status_code == 200
    assert response.json()["fallback_usado"] is True
    assert response.json()["proveedor_utilizado"] is False
    
    monkeypatch.setattr("app.modules.chat.interfaces.routes.interpretar_necesidad_comercial", MagicMock(side_effect=LLMProviderError("provider error")))
    response = client.post("/chat/presupuestacion/interpretar", json={"necesidad": "hola"})
    assert response.status_code == 200
    assert response.json()["fallback_usado"] is True
    app.dependency_overrides.clear()

def test_generar_propuesta_material_not_found():
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = None
    app.dependency_overrides[get_material_repository] = lambda: mock_repo
    app.dependency_overrides[get_current_user] = lambda: MagicMock(id=1, rol="cliente")
    client = TestClient(app)
    response = client.post("/chat/presupuestacion/propuesta", json={
        "material_id": 999, 
        "cantidad": 10.0, 
        "fase_obra": "general", 
        "tolerancia_riesgo": "media",
        "horizonte_meses": 3
    })
    assert response.status_code == 404
    app.dependency_overrides.clear()

def test_generar_propuesta_llm_errors(monkeypatch):
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = MagicMock(id=1, nombre="M1")
    app.dependency_overrides[get_material_repository] = lambda: mock_repo
    app.dependency_overrides[get_current_user] = lambda: MagicMock(id=1, rol="cliente")
    
    monkeypatch.setattr("app.modules.chat.interfaces.routes.generar_propuesta_comercial", MagicMock(side_effect=LLMConfigurationError("config error")))
    client = TestClient(app)
    response = client.post("/chat/presupuestacion/propuesta", json={
        "material_id": 1, 
        "cantidad": 10.0, 
        "fase_obra": "general", 
        "tolerancia_riesgo": "media",
        "horizonte_meses": 3
    })
    assert response.status_code == 503
    
    monkeypatch.setattr("app.modules.chat.interfaces.routes.generar_propuesta_comercial", MagicMock(side_effect=LLMProviderError("provider error")))
    response = client.post("/chat/presupuestacion/propuesta", json={
        "material_id": 1, 
        "cantidad": 10.0, 
        "fase_obra": "general", 
        "tolerancia_riesgo": "media",
        "horizonte_meses": 3
    })
    assert response.status_code == 502
    app.dependency_overrides.clear()
