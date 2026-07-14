from app.modules.chat.application.response_validation import deterministic_grounded_fallback, validate_grounded_response
from app.modules.chat.application.service import answer_question


class UnsafeClient:
    provider_name = "simulated"

    def complete(self, _messages):
        return "Cemento Portland cuesta ARS 100 y conviene comprar ahora."


def test_rejects_invented_amount_and_decision() -> None:
    context = "- Material seleccionado: Cemento Portland.\n- Decision del motor: POSTERGAR.\n- Precio: ARS 200000."
    result = validate_grounded_response("Conviene comprar ahora por ARS 100.", context=context)
    assert result.valid is False
    assert any(reason.startswith("unsupported_numbers") for reason in result.reasons)
    assert "decision_mismatch" in result.reasons


def test_accepts_only_grounded_facts() -> None:
    context = "- Material seleccionado: Cemento Portland.\n- Horizonte: 6 meses.\n- Precio: ARS 200000."
    result = validate_grounded_response("Cemento Portland cuesta ARS 200000 al horizonte de 6 meses.", context=context)
    assert result.valid is True


def test_deterministic_fallback_uses_context_facts() -> None:
    fallback = deterministic_grounded_fallback("HEADER\n- Precio: ARS 200000.\n- Decision: POSTERGAR.")
    assert fallback == "BuildWise informa: Precio: ARS 200000. Decision: POSTERGAR."


def test_answer_replaces_unsafe_provider_output_without_exposing_it() -> None:
    result = answer_question(
        "Qué recomienda BuildWise para cemento?",
        UnsafeClient(),
        context="- Material seleccionado: Cemento Portland.\n- Precio: ARS 200000.\n- Decision del motor: POSTERGAR.",
    )
    assert result.fallback_usado is True
    assert result.validacion_respuesta.startswith("rejected:")
    assert "ARS 100" not in result.respuesta
    assert "POSTERGAR" in result.respuesta
