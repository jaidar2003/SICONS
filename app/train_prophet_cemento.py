from dataclasses import dataclass
from pathlib import Path

import cmdstanpy
from sqlalchemy import select

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import ProphetRow, construir_dataset_prophet
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.shared.database.session import SessionLocal


@dataclass(frozen=True)
class PrediccionFold:
    fold: int
    modelo: str
    ds: str
    y: float
    yhat: float
    abs_error: float
    ape: float


@dataclass(frozen=True)
class ResumenModelo:
    nombre: str
    mae_promedio: float
    mape_promedio: float
    folds_evaluados: int


def _importar_dependencias_prophet():
    try:
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise RuntimeError(
            "Faltan dependencias para entrenar Prophet. Instala al menos `pandas` y `prophet` en tu entorno."
        ) from exc
    return pd, Prophet, CmdStanPyBackend, IStanBackend


def _configurar_cmdstan(CmdStanPyBackend, IStanBackend) -> None:
    cmdstan_global = Path.home() / ".cmdstan" / "cmdstan-2.38.0"
    if not cmdstan_global.exists():
        raise RuntimeError(
            "No se encontro CmdStan en ~/.cmdstan/cmdstan-2.38.0. Ejecuta `python -c \"import cmdstanpy; cmdstanpy.install_cmdstan()\"`."
        )

    cmdstanpy.set_cmdstan_path(str(cmdstan_global))

    def fixed_init(self):
        cmdstanpy.set_cmdstan_path(str(cmdstan_global))
        IStanBackend.__init__(self)

    CmdStanPyBackend.__init__ = fixed_init


def _obtener_serie_mensual_cemento() -> list[PrecioSerieInput]:
    with SessionLocal() as db:
        material = db.scalar(select(Material).where(Material.nombre == "Cemento Portland"))
        if material is None:
            raise RuntimeError("No existe el material Cemento Portland en la base")

        stmt = (
            select(PrecioHistorico)
            .where(PrecioHistorico.material_id == material.id)
            .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
        )
        registros = [
            PrecioSerieInput(
                fecha=precio.fecha,
                precio_normalizado=precio.precio_normalizado,
                unidad_base=material.unidad_base,
                fuente=precio.fuente.nombre if precio.fuente else None,
                numero_comprobante=precio.numero_comprobante,
            )
            for precio in db.scalars(stmt)
        ]
    return construir_serie_mensual(registros)


def _a_dataframe(pd, filas: list[ProphetRow]):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def _predicciones_a_registros(modelo: str, fold: int, evaluacion_df) -> list[PrediccionFold]:
    return [
        PrediccionFold(
            fold=fold,
            modelo=modelo,
            ds=fila.ds.strftime("%Y-%m-%d"),
            y=float(fila.y),
            yhat=float(fila.yhat),
            abs_error=float(fila.abs_error),
            ape=float(fila.ape),
        )
        for fila in evaluacion_df.itertuples()
    ]


def _evaluar_baseline_ultimo_valor(pd, fold: int, train: list[ProphetRow], test: list[ProphetRow]) -> list[PrediccionFold]:
    ultimo_valor = train[-1].y
    test_df = _a_dataframe(pd, test).copy()
    test_df["yhat"] = ultimo_valor
    test_df["abs_error"] = (test_df["y"] - test_df["yhat"]).abs()
    test_df["ape"] = test_df["abs_error"] / test_df["y"] * 100
    return _predicciones_a_registros("baseline_ultimo_valor", fold, test_df)


def _evaluar_promedio_movil(pd, fold: int, train: list[ProphetRow], test: list[ProphetRow], ventana: int = 3) -> list[PrediccionFold]:
    historial = [fila.y for fila in train]
    predicciones: list[PrediccionFold] = []
    for fila in test:
        ventana_actual = historial[-ventana:] if len(historial) >= ventana else historial
        yhat = sum(ventana_actual) / len(ventana_actual)
        abs_error = abs(fila.y - yhat)
        predicciones.append(
            PrediccionFold(
                fold=fold,
                modelo="promedio_movil_3m",
                ds=fila.ds.isoformat(),
                y=fila.y,
                yhat=yhat,
                abs_error=abs_error,
                ape=(abs_error / fila.y) * 100,
            )
        )
        historial.append(fila.y)
    return predicciones


def _evaluar_tendencia_lineal(fold: int, train: list[ProphetRow], test: list[ProphetRow]) -> list[PrediccionFold]:
    n = len(train)
    xs = list(range(n))
    ys = [fila.y for fila in train]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    denominador = sum((x - x_mean) ** 2 for x in xs)
    pendiente = 0.0 if denominador == 0 else sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominador
    intercepto = y_mean - (pendiente * x_mean)

    predicciones: list[PrediccionFold] = []
    for paso, fila in enumerate(test, start=1):
        x = n + paso - 1
        yhat = intercepto + (pendiente * x)
        abs_error = abs(fila.y - yhat)
        predicciones.append(
            PrediccionFold(
                fold=fold,
                modelo="tendencia_lineal",
                ds=fila.ds.isoformat(),
                y=fila.y,
                yhat=yhat,
                abs_error=abs_error,
                ape=(abs_error / fila.y) * 100,
            )
        )
    return predicciones


def _evaluar_prophet(pd, Prophet, fold: int, nombre: str, parametros: dict, train: list[ProphetRow], test: list[ProphetRow]) -> list[PrediccionFold]:
    train_df = _a_dataframe(pd, train)
    test_df = _a_dataframe(pd, test)
    modelo = Prophet(stan_backend="CMDSTANPY", **parametros)
    modelo.fit(train_df)
    futuro = modelo.make_future_dataframe(periods=len(test_df), freq="MS")
    forecast = modelo.predict(futuro)[["ds", "yhat"]]
    evaluacion = test_df.merge(forecast, on="ds", how="left")
    evaluacion["abs_error"] = (evaluacion["y"] - evaluacion["yhat"]).abs()
    evaluacion["ape"] = evaluacion["abs_error"] / evaluacion["y"] * 100
    return _predicciones_a_registros(nombre, fold, evaluacion)


def _resumir_modelos(predicciones: list[PrediccionFold]) -> list[ResumenModelo]:
    agrupados: dict[str, list[PrediccionFold]] = {}
    for prediccion in predicciones:
        agrupados.setdefault(prediccion.modelo, []).append(prediccion)

    resumenes = [
        ResumenModelo(
            nombre=modelo,
            mae_promedio=sum(item.abs_error for item in items) / len(items),
            mape_promedio=sum(item.ape for item in items) / len(items),
            folds_evaluados=len({item.fold for item in items}),
        )
        for modelo, items in agrupados.items()
    ]
    return sorted(resumenes, key=lambda item: item.mae_promedio)


def main() -> None:
    pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias_prophet()
    _configurar_cmdstan(CmdStanPyBackend, IStanBackend)

    serie_mensual = _obtener_serie_mensual_cemento()
    dataset = construir_dataset_prophet(serie_mensual, objetivo="precio_promedio_normalizado")
    folds = construir_folds_temporales(dataset, min_train_size=24, test_size=3, step_size=3)

    configuraciones_prophet = [
        (
            "prophet_default",
            {
                "daily_seasonality": False,
                "weekly_seasonality": False,
                "yearly_seasonality": True,
            },
        ),
        (
            "prophet_suave",
            {
                "daily_seasonality": False,
                "weekly_seasonality": False,
                "yearly_seasonality": True,
                "changepoint_prior_scale": 0.05,
                "seasonality_mode": "additive",
            },
        ),
        (
            "prophet_rigido",
            {
                "daily_seasonality": False,
                "weekly_seasonality": False,
                "yearly_seasonality": False,
                "changepoint_prior_scale": 0.01,
                "seasonality_mode": "additive",
            },
        ),
    ]

    predicciones: list[PrediccionFold] = []
    for fold in folds:
        predicciones.extend(_evaluar_baseline_ultimo_valor(pd, fold.indice, fold.train, fold.test))
        predicciones.extend(_evaluar_promedio_movil(pd, fold.indice, fold.train, fold.test))
        predicciones.extend(_evaluar_tendencia_lineal(fold.indice, fold.train, fold.test))
        for nombre, parametros in configuraciones_prophet:
            predicciones.extend(_evaluar_prophet(pd, Prophet, fold.indice, nombre, parametros, fold.train, fold.test))

    resumenes = _resumir_modelos(predicciones)
    mejor_modelo = resumenes[0].nombre
    mejores_predicciones = [item for item in predicciones if item.modelo == mejor_modelo]

    print(f"Puntos mensuales totales: {len(dataset)}")
    print(f"Folds temporales: {len(folds)}")
    print("Ventana de test por fold: 3 meses")
    print("")
    print("Ranking agregado por backtesting temporal:")
    for resumen in resumenes:
        print(
            f"- {resumen.nombre}: MAE={resumen.mae_promedio:.2f} | "
            f"MAPE={resumen.mape_promedio:.2f}% | folds={resumen.folds_evaluados}"
        )
    print("")
    print(f"Mejor modelo: {mejor_modelo}")
    print("Predicciones del mejor modelo:")
    for prediccion in mejores_predicciones:
        print(
            f"fold={prediccion.fold} ds={prediccion.ds} y={prediccion.y:.4f} "
            f"yhat={prediccion.yhat:.4f} abs_error={prediccion.abs_error:.4f} ape={prediccion.ape:.2f}%"
        )


if __name__ == "__main__":
    main()
