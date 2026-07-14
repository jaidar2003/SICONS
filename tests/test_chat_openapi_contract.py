import hashlib
import json

from app.main import app

EXPECTED_CHAT_PATHS = {
    "/chat/auditoria",
    "/chat/auditoria/determinismo",
    "/chat/auditoria/determinismo/canonicas",
    "/chat/auditoria/metricas",
    "/chat/config",
    "/chat/consultas",
    "/chat/conversaciones",
    "/chat/conversaciones/{conversation_id}",
    "/chat/conversaciones/{conversation_id}/mensajes",
    "/chat/presupuestacion/interpretar",
    "/chat/presupuestacion/propuesta",
    "/chat/status",
}
EXPECTED_CONTRACT_SHA256 = "4f8c73f70593fa695fc3bdde45d394cb59020a02a069760834211d73e0b49cbb"


def test_chat_openapi_contract_is_preserved() -> None:
    schema = app.openapi()
    chat_paths = {path: value for path, value in schema["paths"].items() if path.startswith("/chat")}
    assert set(chat_paths) == EXPECTED_CHAT_PATHS

    contract = {
        path: {
            method: {
                "operationId": operation.get("operationId"),
                "tags": operation.get("tags"),
                "parameters": operation.get("parameters"),
                "requestBody": operation.get("requestBody"),
                "responses": operation.get("responses"),
                "security": operation.get("security"),
            }
            for method, operation in path_item.items()
            if method in {"get", "post", "patch", "delete"}
        }
        for path, path_item in chat_paths.items()
    }
    normalized = json.dumps(contract, sort_keys=True, indent=2).encode()
    assert hashlib.sha256(normalized).hexdigest() == EXPECTED_CONTRACT_SHA256

    operations = [operation for item in contract.values() for operation in item.values()]
    assert all(any(parameter["name"] == "authorization" for parameter in operation["parameters"]) for operation in operations)


def test_chat_routes_are_registered_once() -> None:
    registrations = [
        (route.path, tuple(sorted(route.methods or ())))
        for route in app.routes
        if getattr(route, "path", "").startswith("/chat")
    ]
    assert len(registrations) == len(set(registrations))
