from typing import Any

import httpx

from app.shared.config.settings import settings


class LLMConfigurationError(Exception):
    """Raised when the chat provider has not been configured."""


class LLMProviderError(Exception):
    """Raised when the chat provider fails or responds with an invalid payload."""


class FallbackChatClient:
    def __init__(self, primary, fallback) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_provider_name = getattr(primary, "provider_name", "facultad")
        self.last_fallback_used = False

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            response = self.primary.complete(messages)
            self.last_provider_name = getattr(self.primary, "provider_name", "facultad")
            self.last_fallback_used = False
            return response
        except (LLMConfigurationError, LLMProviderError) as primary_exc:
            try:
                response = self.fallback.complete(messages)
            except (LLMConfigurationError, LLMProviderError) as fallback_exc:
                primary_name = getattr(self.primary, "provider_name", "proveedor primario")
                fallback_name = getattr(self.fallback, "provider_name", "fallback")
                raise LLMProviderError(
                    f"No fue posible obtener respuesta del proveedor primario ({primary_name}) "
                    f"ni del fallback ({fallback_name}). Detalle primario: {primary_exc}. "
                    f"Detalle fallback: {fallback_exc}"
                ) from fallback_exc
            self.last_provider_name = getattr(self.fallback, "provider_name", "claude")
            self.last_fallback_used = True
            return response


class OpenAICompatibleChatClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.openai_base_url or "").rstrip("/")
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model if model is not None else settings.openai_model
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.openai_timeout_seconds
        self.provider_name = "facultad"

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.base_url or not self.api_key or not self.model:
            raise LLMConfigurationError("La integracion de IA no esta configurada.")

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            response = httpx.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError("No fue posible obtener una respuesta del proveedor de IA.") from exc

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError("El proveedor de IA devolvio una respuesta invalida.") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("El proveedor de IA devolvio una respuesta vacia.")
        return content.strip()


class AnthropicChatClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        api_version: str | None = None,
        max_tokens: int | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.base_url = (base_url if base_url is not None else settings.anthropic_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.anthropic_api_key
        self.model = model if model is not None else settings.anthropic_model
        self.api_version = api_version if api_version is not None else settings.anthropic_version
        self.max_tokens = max_tokens if max_tokens is not None else settings.anthropic_max_tokens
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.openai_timeout_seconds
        self.provider_name = "claude"

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.base_url or not self.api_key or not self.model:
            raise LLMConfigurationError("La integracion de Claude no esta configurada.")

        system = "\n".join(message["content"] for message in messages if message["role"] == "system")
        conversation = [message for message in messages if message["role"] != "system"]
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": conversation,
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }
        try:
            response = httpx.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError("No fue posible obtener una respuesta de Claude.") from exc

        try:
            contents = response.json()["content"]
            text = "\n".join(block["text"] for block in contents if block.get("type") == "text")
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMProviderError("Claude devolvio una respuesta invalida.") from exc

        if not text.strip():
            raise LLMProviderError("Claude devolvio una respuesta vacia.")
        return text.strip()
