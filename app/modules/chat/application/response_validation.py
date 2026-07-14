import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.modules.chat.application.interpretation import MATERIAL_ALIASES, normalize_text

_DECISIONS = {"COMPRAR_AHORA", "POSTERGAR", "ESCALONAR", "SIN_VENTAJA_CLARA", "MONITOREAR"}


@dataclass(frozen=True)
class ResponseValidation:
    valid: bool
    reasons: tuple[str, ...] = ()


def _number(value: str) -> str | None:
    cleaned = value.replace(".", "").replace(",", ".") if "," in value else value
    try:
        return format(Decimal(cleaned).normalize(), "f")
    except InvalidOperation:
        return None


def _numbers(text: str) -> set[str]:
    return {number for raw in re.findall(r"(?<![\w-])\d+(?:[.,]\d+)?", text) if (number := _number(raw)) is not None}


def validate_grounded_response(response: str, *, context: str, user_message: str = "") -> ResponseValidation:
    allowed_numbers = _numbers(context) | _numbers(user_message)
    unexpected_numbers = _numbers(response) - allowed_numbers
    reasons = []
    if unexpected_numbers:
        reasons.append(f"unsupported_numbers:{','.join(sorted(unexpected_numbers))}")

    normalized_context = normalize_text(context)
    normalized_response = normalize_text(response)
    context_decisions = {decision for decision in _DECISIONS if decision.lower() in normalized_context.replace(" ", "_")}
    response_decisions = {decision for decision in _DECISIONS if decision.lower().replace("_", " ") in normalized_response}
    if response_decisions and not response_decisions.issubset(context_decisions):
        reasons.append("decision_mismatch")

    mentioned_materials = {
        key for key, aliases in MATERIAL_ALIASES.items() if any(alias in normalized_response for alias in aliases)
    }
    grounded_materials = {
        key for key, aliases in MATERIAL_ALIASES.items() if any(alias in normalized_context for alias in aliases)
    }
    if mentioned_materials - grounded_materials:
        reasons.append("material_mismatch")
    return ResponseValidation(valid=not reasons, reasons=tuple(reasons))


def deterministic_grounded_fallback(context: str) -> str:
    facts = [line[2:].strip() for line in context.splitlines() if line.startswith("- ")]
    if not facts:
        return "No pude validar la redaccion del proveedor con los datos recuperados por BuildWise."
    return "BuildWise informa: " + " ".join(facts[:6])
