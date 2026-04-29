from datetime import date

import pytest

from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import ProphetRow


def _row(year: int, month: int, value: float) -> ProphetRow:
    return ProphetRow(ds=date(year, month, 1), y=value)


def test_construir_folds_temporales_genera_folds_ordenados() -> None:
    dataset = [
        _row(2026, 1, 10.0),
        _row(2026, 2, 11.0),
        _row(2026, 3, 12.0),
        _row(2026, 4, 13.0),
        _row(2026, 5, 14.0),
        _row(2026, 6, 15.0),
    ]

    folds = construir_folds_temporales(dataset, min_train_size=3, test_size=2, step_size=1)

    assert len(folds) == 2
    assert [item.ds for item in folds[0].train] == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    assert [item.ds for item in folds[0].test] == [date(2026, 4, 1), date(2026, 5, 1)]
    assert [item.ds for item in folds[1].train] == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]
    assert [item.ds for item in folds[1].test] == [date(2026, 5, 1), date(2026, 6, 1)]


def test_construir_folds_temporales_rechaza_series_cortas() -> None:
    dataset = [_row(2026, 1, 10.0), _row(2026, 2, 11.0), _row(2026, 3, 12.0)]

    with pytest.raises(ValueError, match="suficientes puntos"):
        construir_folds_temporales(dataset, min_train_size=3, test_size=2)
