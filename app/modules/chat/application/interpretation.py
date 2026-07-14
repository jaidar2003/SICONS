import re
import unicodedata
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Literal

from app.modules.chat.domain.commercial_units import CURRENT_CEMENT_BAG_KG

Intent = Literal["HISTORICO", "FORECAST", "RECOMENDACION", "PRESUPUESTO", "CATALOGO", "ADMIN", "FUERA_ALCANCE"]
Origin = Literal["explicit", "inherited", "inferred", "missing", "ambiguous"]


@dataclass(frozen=True)
class InterpretedField:
    value: object | None
    origin: Origin
    confidence: Literal["high", "medium", "low"] = "high"
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConversationalInterpretation:
    intent: InterpretedField
    material: InterpretedField
    quantity: InterpretedField
    input_unit: InterpretedField
    normalized_quantity: InterpretedField
    base_unit: InterpretedField
    budget: InterpretedField
    horizon_months: InterpretedField
    missing_fields: tuple[str, ...] = ()
    ambiguous_fields: tuple[str, ...] = ()
    requires_confirmation: bool = False
    security_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConversationState:
    intent: str | None = None
    material_key: str | None = None
    horizon_months: int | None = None
    quantity: Decimal | None = None
    input_unit: str | None = None
    budget: Decimal | None = None


MATERIAL_ALIASES = {
    "cemento-portland": ("cemento portland", "cemento", "portland", "semento", "sementoo", "cemnto"),
    "pastina": ("pastina", "pastina klaukol", "klaukol"),
    "membrana-megaflex": ("membrana megaflex", "membrana", "megaflex", "membrana asfaltica"),
}

_NUMBER_WORDS = {
    "una": 1,
    "uno": 1,
    "tres": 3,
    "seis": 6,
    "doce": 12,
    "treinta": 30,
    "treinte": 30,
}

_INJECTION_PATTERNS = (
    r"ignora(?:r|) (?:las |tus |)reglas",
    r"prompt (?:del |de |)sistema",
    r"api[ _-]?key",
    r"ejecuta(?:r|) (?:una |)consulta sql",
    r"actua como administrador",
    r"no registres (?:esta |la |)consulta",
    r"inventa(?:r|) (?:un |una |)precio",
    r"inventa(?:r|) (?:un |una |)recomendacion",
    r"usa(?:r|) un mape",
    r"decime que conviene comprar aunque",
)


def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode("ascii")


def _decimal(raw: str) -> Decimal | None:
    value = raw.strip().lower().replace("$", "").replace("ars", "").strip()
    multiplier = Decimal("1000") if re.search(r"(?:\bmil\b|k)$", value) else Decimal("1")
    value = re.sub(r"\s*(?:mil|k)$", "", value).strip()
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", value):
        value = value.replace(".", "").replace(",", "")
    else:
        value = value.replace(",", ".")
    try:
        result = Decimal(value) * multiplier
    except InvalidOperation:
        return None
    return result if result > 0 else None


def classify_intent(text: str, inherited: str | None = None) -> InterpretedField:
    normalized = normalize_text(text)
    rules = (
        ("ADMIN", r"\b(usuario|usuarios|margen|margenes|habilitar|eliminar usuario|registrar precio)\b"),
        ("PRESUPUESTO", r"\b(presupuesto|cotiza|cotizacion|propuesta|me alcanza|tengo \$?|necesito(?: comprar)?|quiero comprar)\b"),
        ("RECOMENDACION", r"\b(conviene|recomendacion|comprar ahora|compro|esperar|decision|estrategia|optimizar|comparar estrategias)\b"),
        ("FORECAST", r"\b(forecast|proyeccion|proyectad[oa]|mape|mae|confiable|confiabilidad|modelo|anomalia)\b"),
        ("HISTORICO", r"\b(ultimo precio|precio historico|historico|historial|evoluci(?:on|ono)|aument[oa]|costaba|costaban|fuente)\b"),
        ("CATALOGO", r"\b(catalogo|materiales|presentaciones|productos)\b"),
    )
    for intent, pattern in rules:
        if re.search(pattern, normalized):
            return InterpretedField(intent, "explicit")
    known_material = any(any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases) for aliases in MATERIAL_ALIASES.values())
    if known_material and re.search(r"\b(?:\d+|un|uno|tres|seis|doce)\s+mes", normalized):
        return InterpretedField("FORECAST", "inferred", "medium")
    if inherited and re.fullmatch(r"[?\s]*(y|ahora|eso|a)?(?:\s+la\s+[a-z]+)?(?:\s+a)?\s*(?:\d+|un|uno|tres|seis|doce)?\s*(?:mes|meses)?[?\s]*", normalized):
        return InterpretedField(inherited, "inherited")
    if inherited and re.search(r"\b(?:\d+|un|uno|tres|seis|doce)\s+mes", normalized):
        return InterpretedField(inherited, "inherited")
    return InterpretedField("FUERA_ALCANCE", "inferred", "medium")


def resolve_material(text: str, inherited: str | None = None) -> InterpretedField:
    normalized = normalize_text(text)
    exact = []
    for key, aliases in MATERIAL_ALIASES.items():
        if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in aliases):
            exact.append(key)
    if len(exact) == 1:
        return InterpretedField(exact[0], "explicit")
    if len(exact) > 1:
        return InterpretedField(None, "ambiguous", "low", tuple(exact))

    words = re.findall(r"[a-z]{5,}", normalized)
    candidates = []
    for word in words:
        for key, aliases in MATERIAL_ALIASES.items():
            score = max(SequenceMatcher(None, word, alias.split()[0]).ratio() for alias in aliases)
            if score >= 0.78:
                candidates.append((score, key))
    if candidates:
        candidates.sort(reverse=True)
        best = candidates[0]
        alternatives = tuple(sorted({key for score, key in candidates if best[0] - score < 0.04}))
        if len(alternatives) == 1:
            return InterpretedField(best[1], "inferred", "medium")
        return InterpretedField(None, "ambiguous", "low", alternatives)
    if inherited:
        return InterpretedField(inherited, "inherited")
    return InterpretedField(None, "missing", "low")


def extract_horizon(text: str, inherited: int | None = None) -> InterpretedField:
    normalized = normalize_text(text)
    match = re.search(r"\b(\d{1,2}|un|uno|tres|seis|doce)\s*mes(?:es)?\b", normalized)
    if match:
        raw = match.group(1)
        value = int(raw) if raw.isdigit() else _NUMBER_WORDS["uno" if raw == "un" else raw]
        if 1 <= value <= 12:
            return InterpretedField(value, "explicit")
        return InterpretedField(None, "ambiguous", "low", ("1-12 meses",))
    if "mes que viene" in normalized:
        return InterpretedField(1, "inferred")
    if inherited is not None:
        return InterpretedField(inherited, "inherited")
    return InterpretedField(None, "missing")


def extract_quantity(text: str, material_key: str | None) -> tuple[InterpretedField, InterpretedField, InterpretedField, InterpretedField]:
    normalized = normalize_text(text)
    match = re.search(r"\b(\d+(?:[.,]\d+)?|treinta|treinte)\s*(bolsas?|kg|kilos?|toneladas?)\b", normalized)
    if not match:
        missing = InterpretedField(None, "missing")
        return missing, missing, missing, missing
    raw, unit_raw = match.groups()
    value = Decimal(_NUMBER_WORDS[raw]) if raw in _NUMBER_WORDS else _decimal(raw)
    if value is None:
        invalid = InterpretedField(None, "ambiguous", "low")
        return invalid, invalid, invalid, invalid
    if unit_raw.startswith("bolsa"):
        unit = "bag"
        if material_key == "cemento-portland":
            normalized_value = value * CURRENT_CEMENT_BAG_KG
            return (
                InterpretedField(value, "explicit"),
                InterpretedField(unit, "explicit"),
                InterpretedField(normalized_value, "inferred"),
                InterpretedField("kg", "inferred"),
            )
        return InterpretedField(value, "explicit"), InterpretedField(unit, "explicit"), InterpretedField(None, "ambiguous", "low"), InterpretedField(None, "ambiguous", "low")
    factor = Decimal("1000") if unit_raw.startswith("tonelada") else Decimal("1")
    return (
        InterpretedField(value, "explicit"),
        InterpretedField("tonne" if factor == 1000 else "kg", "explicit"),
        InterpretedField(value * factor, "inferred" if factor != 1 else "explicit"),
        InterpretedField("kg", "explicit"),
    )


def extract_budget(text: str, inherited: Decimal | None = None) -> InterpretedField:
    normalized = normalize_text(text)
    patterns = (
        r"(?:presupuesto(?: de)?|tengo|me alcanza con)\s*(?:ars\s*)?\$?\s*([\d.,]+\s*(?:mil|k)?)",
        r"(?:ars|\$)\s*([\d.,]+\s*(?:mil|k)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            value = _decimal(match.group(1))
            return InterpretedField(value, "explicit") if value else InterpretedField(None, "ambiguous", "low")
    if inherited is not None:
        return InterpretedField(inherited, "inherited")
    return InterpretedField(None, "missing")


def interpret_query(text: str, state: ConversationState | None = None) -> ConversationalInterpretation:
    state = state or ConversationState()
    intent = classify_intent(text, state.intent)
    material = resolve_material(text, state.material_key)
    horizon = extract_horizon(text, state.horizon_months)
    quantity, unit, normalized_quantity, base_unit = extract_quantity(text, material.value if isinstance(material.value, str) else None)
    budget = extract_budget(text)

    # Commercial quantities and budgets never leak into an unrelated material or a later request.
    if intent.origin == "inherited" and state.intent == "PRESUPUESTO" and material.origin == "inherited":
        if quantity.value is None and state.quantity is not None:
            quantity = replace(quantity, value=state.quantity, origin="inherited")
            unit = replace(unit, value=state.input_unit, origin="inherited")
        if budget.value is None and state.budget is not None:
            budget = replace(budget, value=state.budget, origin="inherited")

    ambiguous = tuple(name for name, value in (("material", material), ("quantity", quantity), ("budget", budget), ("horizon", horizon)) if value.origin == "ambiguous")
    required = {"FORECAST": ("material", "horizon"), "RECOMENDACION": ("material", "horizon"), "PRESUPUESTO": ("material",)}
    values = {"material": material, "quantity": quantity, "budget": budget, "horizon": horizon}
    missing = tuple(name for name in required.get(str(intent.value), ()) if values[name].value is None)
    flags = tuple(pattern for pattern in _INJECTION_PATTERNS if re.search(pattern, normalize_text(text)))
    return ConversationalInterpretation(
        intent=intent,
        material=material,
        quantity=quantity,
        input_unit=unit,
        normalized_quantity=normalized_quantity,
        base_unit=base_unit,
        budget=budget,
        horizon_months=horizon,
        missing_fields=missing,
        ambiguous_fields=ambiguous,
        requires_confirmation=bool(missing or ambiguous),
        security_flags=flags,
    )
