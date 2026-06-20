from unittest.mock import MagicMock

import httpx
import pytest

from app.modules.chat.infrastructure.llm_client import (
    AnthropicChatClient,
    FallbackChatClient,
    LLMConfigurationError,
    LLMProviderError,
    OpenAICompatibleChatClient,
)


def test_openai_client_config_error():
    client = OpenAICompatibleChatClient(base_url="", api_key="", model="")
    with pytest.raises(LLMConfigurationError):
        client.complete([])

def test_openai_client_http_error(monkeypatch):
    client = OpenAICompatibleChatClient(base_url="http://api", api_key="key", model="m")
    
    def mock_post(*args, **kwargs):
        raise httpx.HTTPError("error")
    
    monkeypatch.setattr(httpx, "post", mock_post)
    with pytest.raises(LLMProviderError, match="No fue posible obtener una respuesta"):
        client.complete([{"role": "user", "content": "hi"}])

def test_openai_client_http_error_incluye_estado_y_detalle(monkeypatch):
    request = httpx.Request("POST", "https://example.test/chat/completions")
    response = httpx.Response(401, json={"detail": "token vencido"}, request=request)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    client = OpenAICompatibleChatClient(base_url="https://example.test", api_key="token", model="model")

    with pytest.raises(LLMProviderError, match="HTTP 401: token vencido"):
        client.complete([{"role": "user", "content": "hola"}])

def test_openai_client_invalid_json(monkeypatch):
    client = OpenAICompatibleChatClient(base_url="http://api", api_key="key", model="m")
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"bad": "json"}
    mock_resp.raise_for_status = lambda: None
    
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: mock_resp)
    with pytest.raises(LLMProviderError, match="respuesta invalida"):
        client.complete([{"role": "user", "content": "hi"}])

def test_openai_client_empty_response(monkeypatch):
    client = OpenAICompatibleChatClient(base_url="http://api", api_key="key", model="m")
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": "  "}}]}
    mock_resp.raise_for_status = lambda: None
    
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: mock_resp)
    with pytest.raises(LLMProviderError, match="respuesta vacia"):
        client.complete([{"role": "user", "content": "hi"}])

def test_anthropic_client_config_error():
    client = AnthropicChatClient(base_url="", api_key="", model="")
    with pytest.raises(LLMConfigurationError):
        client.complete([])

def test_anthropic_client_http_error(monkeypatch):
    client = AnthropicChatClient(base_url="http://api", api_key="key", model="m")
    
    def mock_post(*args, **kwargs):
        raise httpx.HTTPError("error")
    
    monkeypatch.setattr(httpx, "post", mock_post)
    with pytest.raises(LLMProviderError, match="No fue posible obtener una respuesta de Claude"):
        client.complete([{"role": "user", "content": "hi"}])

def test_anthropic_client_invalid_json(monkeypatch):
    client = AnthropicChatClient(base_url="http://api", api_key="key", model="m")
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"bad": "json"}
    mock_resp.raise_for_status = lambda: None
    
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: mock_resp)
    with pytest.raises(LLMProviderError, match="Claude devolvio una respuesta invalida"):
        client.complete([{"role": "user", "content": "hi"}])

def test_anthropic_client_empty_response(monkeypatch):
    client = AnthropicChatClient(base_url="http://api", api_key="key", model="m")
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"content": []}
    mock_resp.raise_for_status = lambda: None
    
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: mock_resp)
    with pytest.raises(LLMProviderError, match="Claude devolvio una respuesta vacia"):
        client.complete([{"role": "user", "content": "hi"}])


def test_fallback_chat_client_usa_fallback_si_falla_el_primario():
    class FailingClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            raise LLMProviderError("primary down")

    class WorkingClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            return "Respuesta de fallback"

    primary = FailingClient()
    fallback = WorkingClient()
    client = FallbackChatClient(primary, fallback)

    response = client.complete([{"role": "user", "content": "hi"}])

    assert response == "Respuesta de fallback"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_fallback_chat_client_reporta_ambos_errores_si_fallan_ambos():
    class FailingClient:
        def __init__(self, provider_name, message) -> None:
            self.provider_name = provider_name
            self.message = message

        def complete(self, messages):
            raise LLMProviderError(self.message)

    client = FallbackChatClient(
        FailingClient("facultad", "um down"),
        FailingClient("claude", "claude down"),
    )

    with pytest.raises(LLMProviderError) as error:
        client.complete([{"role": "user", "content": "hi"}])

    assert "proveedor primario (facultad)" in str(error.value)
    assert "fallback (claude)" in str(error.value)
    assert "um down" in str(error.value)
    assert "claude down" in str(error.value)


def test_fallback_chat_client_prefiere_el_primario():
    class WorkingClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            return "Respuesta primaria"

    class FallbackClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages):
            self.calls += 1
            return "Respuesta fallback"

    primary = WorkingClient()
    fallback = FallbackClient()
    client = FallbackChatClient(primary, fallback)

    response = client.complete([{"role": "user", "content": "hi"}])

    assert response == "Respuesta primaria"
    assert primary.calls == 1
    assert fallback.calls == 0
