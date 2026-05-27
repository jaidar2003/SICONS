from app.modules.pricing.application.model_selector import (
    MATERIAL_KEY_CEMENTO_PORTLAND,
    ORIGEN_DECISION_GLOBAL_FALLBACK,
    ORIGEN_DECISION_MATERIAL_DEFAULT,
    _benchmark_is_supported,
    _parse_float,
    _parse_int,
    resolve_model_selection,
)


def test_parse_float_invalid():
    assert _parse_float("no-un-numero") is None

def test_parse_int_invalid():
    assert _parse_int("no-un-entero") is None

def test_benchmark_is_supported_patterns():
    # Unsupported pattern
    assert _benchmark_is_supported("prophet_lags") is False
    # Not in supported models
    assert _benchmark_is_supported("modelo_desconocido") is False

def test_resolve_model_selection_material_default():
    # Cemento 3 is exact, Cemento 5 should be default
    res = resolve_model_selection(MATERIAL_KEY_CEMENTO_PORTLAND, 5)
    assert res.origen_decision == ORIGEN_DECISION_MATERIAL_DEFAULT
    assert res.horizonte_meses == 5

def test_resolve_model_selection_fallback():
    res = resolve_model_selection("material-desconocido", 3)
    assert res.origen_decision == ORIGEN_DECISION_GLOBAL_FALLBACK
    assert res.modelo == "prophet_base"
