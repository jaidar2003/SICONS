from dataclasses import dataclass
from datetime import date
from math import ceil

from app.modules.pricing.application.series import PuntoSeriePrecio

OBJETIVOS_PROPHET = {
    "precio_promedio_normalizado",
    "precio_equivalente_25kg",
    "precio_equivalente_50kg",
}
BEST_PROPHET_CONFIG = {
    "daily_seasonality": False,
    "weekly_seasonality": False,
    "yearly_seasonality": False,
    "changepoint_prior_scale": 0.01,
    "seasonality_prior_scale": 1.0,
    "seasonality_mode": "additive",
}


@dataclass(frozen=True)
class ProphetRow:
    ds: date
    y: float


@dataclass(frozen=True)
class ProphetSplit:
    train: list[ProphetRow]
    test: list[ProphetRow]


@dataclass(frozen=True)
class ForecastMetrics:
    folds: int
    mae: float
    mape: float


@dataclass(frozen=True)
class ForecastPoint:
    fecha: date
    precio_proyectado: float
    precio_equivalente_25kg: float
    precio_equivalente_50kg: float


def construir_dataset_prophet(
    puntos: list[PuntoSeriePrecio],
    objetivo: str = "precio_equivalente_25kg",
) -> list[ProphetRow]:
    if objetivo not in OBJETIVOS_PROPHET:
        objetivos = ", ".join(sorted(OBJETIVOS_PROPHET))
        raise ValueError(f"Objetivo invalido: {objetivo}. Usa uno de: {objetivos}")

    dataset = [
        ProphetRow(
            ds=punto.fecha,
            y=float(getattr(punto, objetivo)),
        )
        for punto in sorted(puntos, key=lambda punto: punto.fecha)
    ]
    return dataset


def dividir_dataset_prophet(
    dataset: list[ProphetRow],
    proporcion_test: float = 0.2,
) -> ProphetSplit:
    if not 0 < proporcion_test < 1:
        raise ValueError("La proporcion_test debe estar entre 0 y 1")
    if len(dataset) < 2:
        raise ValueError("Se necesitan al menos 2 puntos para dividir train y test")

    dataset_ordenado = sorted(dataset, key=lambda fila: fila.ds)
    cantidad_test = max(1, ceil(len(dataset_ordenado) * proporcion_test))
    cantidad_test = min(cantidad_test, len(dataset_ordenado) - 1)

    corte = len(dataset_ordenado) - cantidad_test
    return ProphetSplit(
        train=dataset_ordenado[:corte],
        test=dataset_ordenado[corte:],
    )


def inicio_mes_siguiente(fecha: date) -> date:
    if fecha.month == 12:
        return date(fecha.year + 1, 1, 1)
    return date(fecha.year, fecha.month + 1, 1)


def sumar_meses(fecha: date, cantidad: int) -> date:
    if cantidad < 0:
        raise ValueError("La cantidad de meses no puede ser negativa")

    month_index = fecha.month - 1 + cantidad
    year = fecha.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def generar_fechas_mensuales(fecha_inicio: date, cantidad: int) -> list[date]:
    if cantidad < 1:
        raise ValueError("La cantidad de fechas debe ser al menos 1")
    return [sumar_meses(fecha_inicio, offset) for offset in range(cantidad)]
