from unittest.mock import MagicMock

import httpx
import pytest

from app.modules.chat.infrastructure.llm_client import (
    AnthropicChatClient,
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
