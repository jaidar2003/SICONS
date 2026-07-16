import re
import unicodedata
from collections.abc import Iterable
from enum import Enum


class HelpTopic(str, Enum):
    CAPABILITIES = "capabilities"
    MATERIALS = "materials"
    BUDGET = "budget"
    MAPE = "mape"
    ANOMALY = "anomaly"
    RECOMMENDATION = "recommendation"
    GREETING = "greeting"


def normalize_question(question: str) -> str:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    words = re.findall(r"[a-z0-9$]+", normalized)
    corrections = {"q": "que", "qe": "que", "ke": "que", "nesesito": "necesito", "combiene": "conviene"}
    return " ".join(corrections.get(word, word) for word in words)


def classify_help_question(question: str) -> HelpTopic | None:
    normalized = normalize_question(question)
    tokens = set(normalized.split())
    if normalized in {"hola", "buenas", "buen dia", "buenas tardes", "buenas noches"}:
        return HelpTopic.GREETING
    if normalized in {"ayuda", "no se por donde empezar", "no se como empezar"}:
        return HelpTopic.CAPABILITIES
    if ({"mape", "error"} & tokens) and ({"significa", "es", "quiere", "explica", "explicame"} & tokens):
        return HelpTopic.MAPE
    if (
        ({"anomalia", "anomalias"} & tokens)
        and ({"significa", "es", "aparece", "explica", "explicame", "por"} & tokens)
        and not ({"cuantas", "cemento", "pastina", "membrana", "forecast"} & tokens)
    ):
        return HelpTopic.ANOMALY
    if ({"recomendacion", "recomienda", "decide", "decision"} & tokens) and ({"como", "funciona", "comprar", "esperar", "explica"} & tokens):
        return HelpTopic.RECOMMENDATION
    if ({"presupuesto", "compra", "comprar"} & tokens) and ({"como", "hago", "calculo", "armar"} & tokens):
        return HelpTopic.BUDGET
    if ({"material", "materiales", "productos"} & tokens) and ({"que", "cuales", "mostrame", "manejan", "hay"} & tokens):
        return HelpTopic.MATERIALS
    capability_phrases = (
        "que puedo hacer",
        "que hace este asistente",
        "para que sirve buildwise",
        "como me podes ayudar",
        "que puedo consultar",
        "que funciones tiene",
        "cuales son tus funciones",
        "como se usa buildwise",
        "como usar buildwise",
    )
    if any(phrase in normalized for phrase in capability_phrases):
        if re.search(r"\d|\$|\bars\b", normalized):
            return None
        return HelpTopic.CAPABILITIES
    return None


def render_help_answer(topic: HelpTopic, *, material_names: Iterable[str] = (), is_admin: bool = False) -> str:
    names = list(material_names)
    if topic == HelpTopic.GREETING:
        return (
            "Hola. Puedo ayudarte a consultar precios, entender proyecciones y evaluar compras de materiales.\n\n"
            "Podemos empezar por: '¿Que materiales hay?', 'ultimo precio del cemento' o 'como hago un presupuesto'."
        )
    if topic == HelpTopic.MAPE:
        return (
            "El MAPE es el error porcentual promedio observado en evaluaciones historicas. Cuanto menor es, menor "
            "fue la desviacion promedio. No es una probabilidad de acierto ni garantiza el futuro.\n\n"
            "Podes seguir con: 'ver el MAPE del cemento', 'consultar la fecha base' o 'ver la proyeccion'."
        )
    if topic == HelpTopic.ANOMALY:
        return (
            "Una anomalia es una variacion de precio fuera del comportamiento esperado. No significa automaticamente "
            "que el dato sea incorrecto: conviene revisar fecha, fuente, presentacion y contexto de compra.\n\n"
            "Podes seguir con: 'ver anomalias del cemento', 'mostrar el historico' o 'explicarlo mas facil'."
        )
    if topic == HelpTopic.RECOMMENDATION:
        return (
            "La recomendacion la calcula BuildWise, no la IA. El motor usa los datos confirmados de la compra, como "
            "material, cantidad, horizonte, presupuesto, precios y proyeccion; despues el asistente explica el resultado.\n\n"
            "Podes seguir con: 'necesito 30 bolsas de cemento', 'tengo 200 mil pesos' o 'comparar con esperar'."
        )
    if topic == HelpTopic.BUDGET:
        return (
            "Para analizar una compra, indicame el material y una cantidad o un presupuesto. Si corresponde, tambien "
            "podes agregar la fecha de necesidad o el horizonte. No tenes que informar cantidad y presupuesto a la vez.\n\n"
            "Ejemplo: 'Necesito 30 bolsas de cemento en agosto y tengo $200.000'."
        )
    if topic == HelpTopic.MATERIALS:
        if not names:
            return (
                "No hay materiales activos disponibles en el catalogo en este momento.\n\n"
                "Podes reintentar mas tarde o consultar al administrador."
            )
        listed = ", ".join(names)
        return (
            f"BuildWise trabaja actualmente con: {listed}.\n\n"
            "Podes seguir con: 'ver precio del cemento', 'comparar materiales' o 'armar un presupuesto'."
        )

    admin_text = " Como administrador, tambien podes gestionar usuarios, margenes y auditoria." if is_admin else ""
    return (
        "Podes consultar materiales y precios, revisar historicos, analizar tendencias y proyecciones, entender el "
        "error historico, revisar anomalias, comparar estrategias y evaluar cantidades o presupuestos. Los calculos "
        f"economicos los realiza BuildWise; el asistente los interpreta y explica.{admin_text}\n\n"
        "Proba con: 'ultimo precio del cemento', 'proyeccion a 3 meses' o "
        "'necesito 30 bolsas y tengo $200.000'."
    )


def unsupported_material_mention(question: str) -> str | None:
    normalized = normalize_question(question)
    unsupported = ("ladrillo", "ladrillos", "arena", "hierro", "yeso", "cal", "ceramico", "ceramicos")
    return next((material for material in unsupported if re.search(rf"\b{material}\b", normalized)), None)


def clarification_answer(
    *,
    intent: str | None,
    material_name: str | None,
    material_names: Iterable[str] = (),
    unsupported_material: str | None = None,
) -> str | None:
    names = list(material_names)
    options = f" Los materiales disponibles son: {', '.join(names)}." if names else ""
    if unsupported_material:
        return f"No encontre '{unsupported_material}' en el catalogo activo.{options} ¿Que material queres consultar?"
    if intent not in {"HISTORICO", "FORECAST", "RECOMENDACION"} or material_name:
        return None
    labels = {
        "HISTORICO": "consultar el historial",
        "FORECAST": "mostrar la proyeccion",
        "RECOMENDACION": "evaluar la compra",
    }
    return f"¿De que material queres {labels[intent]}?{options}"


def unavailable_calculation_answer(*, context: str | None, intent: str | None, material_name: str | None) -> str | None:
    if intent not in {"FORECAST", "RECOMENDACION"} or not context:
        return None
    normalized = normalize_question(context)
    if "no fue posible calcular forecast recomendacion" not in normalized:
        return None
    label = f" para {material_name}" if material_name else ""
    return (
        f"No hay una proyeccion disponible{label} para ese horizonte, por lo que BuildWise no puede calcular una "
        "recomendacion responsable.\n\nPodes cambiar el horizonte, consultar el historico o probar otro material."
    )


def provider_failure_answer(*, context: str | None, intent: str | None) -> str:
    if not context:
        return (
            "No pude generar la explicacion completa en este momento. Podes reintentar o hacer una consulta directa, "
            "por ejemplo: 'ultimo precio del cemento', 'que materiales hay' o 'como hago un presupuesto'."
        )

    facts = []
    for line in context.splitlines():
        if not line.startswith("- "):
            continue
        fact = line[2:].strip()
        if fact.startswith(("No pidas ", "Capacidades conversacionales ", "Las operaciones administrativas ")):
            continue
        fact = fact.replace("Decision del motor:", "Decision calculada por BuildWise:")
        fact = fact.replace("MAPE del modelo:", "Error porcentual promedio (MAPE):")
        fact = fact.replace("La evaluacion economica es por 1 unidad base;", "Sin una cantidad indicada,")
        facts.append(fact)

    if not facts:
        return "No pude generar la explicacion completa. La consulta no modifico ningun calculo y podes reintentar."
    intro = {
        "HISTORICO": "Pude consultar el historico. Esto es lo que BuildWise confirma:",
        "FORECAST": "Pude consultar la proyeccion. Esto es lo que BuildWise confirma:",
        "RECOMENDACION": "Pude calcular la evaluacion. Esto es lo que BuildWise confirma:",
        "PRESUPUESTO": "Pude consultar los datos de compra. Esto es lo que BuildWise confirma:",
    }.get(intent, "Pude consultar los datos. Esto es lo que BuildWise confirma:")
    return intro + "\n" + "\n".join(f"- {fact}" for fact in facts[:7]) + "\n\nPodes reintentar solamente la explicacion."
