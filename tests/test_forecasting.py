from datetime import date
from decimal import Decimal

import pytest

from app.modules.pricing.application.forecasting import (
    ProphetRow,
    construir_dataset_prophet,
    dividir_dataset_prophet,
    generar_fechas_mensuales,
    inicio_mes_siguiente,
    sumar_meses,
)
from app.modules.pricing.application.series import PuntoSeriePrecio


def _punto(fecha: date, precio_25kg: str) -> PuntoSeriePrecio:
    return PuntoSeriePrecio(
        fecha=fecha,
        precio_promedio_normalizado=Decimal(precio_25kg) / Decimal("25"),
        unidad_base="kg",
        precio_equivalente_25kg=Decimal(precio_25kg),
        precio_equivalente_50kg=(Decimal(precio_25kg) / Decimal("25")) * Decimal("50"),
        cantidad_registros=1,
        cantidad_facturas=1,
        fuentes=["Factura compra"],
        variacion_porcentual_anterior=None,
    )


def test_construir_dataset_prophet_ordena_y_mapea_columnas() -> None:
    dataset = construir_dataset_prophet(
        [
            _punto(date(2026, 3, 1), "6800.00"),
            _punto(date(2026, 1, 1), "6200.00"),
            _punto(date(2026, 2, 1), "6500.00"),
        ]
    )

    assert [fila.ds for fila in dataset] == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    assert [fila.y for fila in dataset] == [6200.0, 6500.0, 6800.0]


def test_construir_dataset_prophet_invalid_objetivo():
    with pytest.raises(ValueError, match="Objetivo invalido"):
        construir_dataset_prophet([], objetivo="invalido")


def test_dividir_dataset_prophet_hace_split_cronologico() -> None:
    dataset = construir_dataset_prophet(
        [
            _punto(date(2026, 1, 1), "6200.00"),
            _punto(date(2026, 2, 1), "6500.00"),
            _punto(date(2026, 3, 1), "6800.00"),
            _punto(date(2026, 4, 1), "7000.00"),
            _punto(date(2026, 5, 1), "7200.00"),
        ]
    )

    split = dividir_dataset_prophet(dataset, proporcion_test=0.4)

    assert [fila.ds for fila in split.train] == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
    assert [fila.ds for fila in split.test] == [date(2026, 4, 1), date(2026, 5, 1)]


def test_dividir_dataset_prophet_rechaza_series_muy_cortas() -> None:
    dataset = construir_dataset_prophet([_punto(date(2026, 1, 1), "6200.00")])

    with pytest.raises(ValueError, match="al menos 2 puntos"):
        dividir_dataset_prophet(dataset)


def test_dividir_dataset_prophet_invalid_proporcion():
    with pytest.raises(ValueError, match="debe estar entre 0 y 1"):
        dividir_dataset_prophet([ProphetRow(date(2024, 1, 1), 10.0), ProphetRow(date(2024, 2, 1), 11.0)], proporcion_test=0)


def test_helpers_mensuales_generan_fechas_consecutivas() -> None:
    inicio = inicio_mes_siguiente(date(2026, 3, 1))

    fechas = generar_fechas_mensuales(inicio, 3)

    assert inicio == date(2026, 4, 1)
    assert fechas == [date(2026, 4, 1), date(2026, 5, 1), date(2026, 6, 1)]


def test_sumar_meses_negative():
    with pytest.raises(ValueError, match="no puede ser negativa"):
        sumar_meses(date(2024, 1, 1), -1)


def test_generar_fechas_mensuales_invalid_cantidad():
    with pytest.raises(ValueError, match="debe ser al menos 1"):
        generar_fechas_mensuales(date(2024, 1, 1), 0)
