from app.experiment_prophet_cemento import _grilla_experimentos


def test_grilla_experimentos_tiene_tamano_esperado() -> None:
    grilla = _grilla_experimentos()

    assert len(grilla) == 96
    assert {item.frecuencia for item in grilla} == {"mensual", "diaria"}
    assert {item.horizonte for item in grilla} == {3, 6, 12}
