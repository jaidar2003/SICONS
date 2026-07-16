import re

import pytest

from app.modules.chat.application.conversational_support import (
    HelpTopic,
    classify_help_question,
    render_help_answer,
)

pytestmark = pytest.mark.chat_evaluation

CASES = (
    ("que puedo hacer con este asistente", HelpTopic.CAPABILITIES),
    ("que puedo hacer con esto", HelpTopic.CAPABILITIES),
    ("¿Qué hace este asistente?", HelpTopic.CAPABILITIES),
    ("¿Para qué sirve BuildWise?", HelpTopic.CAPABILITIES),
    ("¿Cómo me podés ayudar?", HelpTopic.CAPABILITIES),
    ("¿Qué puedo consultar?", HelpTopic.CAPABILITIES),
    ("Ayuda.", HelpTopic.CAPABILITIES),
    ("No sé por dónde empezar.", HelpTopic.CAPABILITIES),
    ("ke puedo hacer con esto???", HelpTopic.CAPABILITIES),
    ("qué materiales hay", HelpTopic.MATERIALS),
    ("Mostrame qué materiales manejan.", HelpTopic.MATERIALS),
    ("como hago un presupuesto", HelpTopic.BUDGET),
    ("¿Cómo calculo una compra?", HelpTopic.BUDGET),
    ("qué significa mape", HelpTopic.MAPE),
    ("¿Qué quiere decir ese porcentaje de error?", HelpTopic.MAPE),
    ("qué es una anomalía", HelpTopic.ANOMALY),
    ("¿Por qué aparece una anomalía?", HelpTopic.ANOMALY),
    ("cómo funciona la recomendación", HelpTopic.RECOMMENDATION),
    ("¿Cómo decide si comprar o esperar?", HelpTopic.RECOMMENDATION),
    ("hola", HelpTopic.GREETING),
)


@pytest.mark.parametrize(("question", "expected"), CASES)
def test_contextual_help_canonical_classification(question: str, expected: HelpTopic) -> None:
    assert classify_help_question(question) == expected


@pytest.mark.parametrize("topic", list(HelpTopic))
def test_contextual_help_never_exposes_internal_terminology(topic: HelpTopic) -> None:
    answer = render_help_answer(topic, material_names=["Cemento Portland (kg)"])
    assert not re.search(r"\b(RAG|snapshot|fallback|proveedor|pipeline|excepcion|regresor)\b", answer, re.IGNORECASE)
