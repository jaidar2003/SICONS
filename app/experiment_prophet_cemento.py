from dataclasses import dataclass
from itertools import product
from pathlib import Path

from app.experiments.pricing.common import (
    construir_dataset_material,
    configurar_cmdstan,
    importar_dependencias_prophet,
    obtener_registros_material,
)
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import ProphetRow, construir_dataset_prophet
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios


@dataclass(frozen=True)
class ConfiguracionExperimento:
    frecuencia: str
    horizonte: int
    yearly_seasonality: bool
    changepoint_prior_scale: float
    seasonality_prior_scale: float
    seasonality_mode: str


@dataclass(frozen=True)
class ResultadoExperimento:
    frecuencia: str
    horizonte: int
    yearly_seasonality: bool
    changepoint_prior_scale: float
    seasonality_prior_scale: float
    seasonality_mode: str
    folds: int
    mae: float
    mape: float


def _importar_dependencias_prophet():
    return importar_dependencias_prophet(
        "Faltan dependencias para entrenar Prophet. Instala al menos `pandas` y `prophet` en tu entorno."
    )


def _configurar_cmdstan(CmdStanPyBackend, IStanBackend) -> None:
    configurar_cmdstan(
        CmdStanPyBackend,
        IStanBackend,
        "No se encontro CmdStan en ~/.cmdstan/cmdstan-2.38.0. Ejecuta `python -c \"import cmdstanpy; cmdstanpy.install_cmdstan()\"`.",
    )


def _obtener_registros_cemento() -> list[PrecioSerieInput]:
    _, registros = obtener_registros_material("Cemento Portland")
    return registros


def _construir_dataset(registros: list[PrecioSerieInput], frecuencia: str) -> list[ProphetRow]:
    if frecuencia == "mensual":
        puntos = construir_serie_mensual(registros)
    elif frecuencia == "diaria":
        puntos = construir_serie_precios(registros)
    else:
        raise ValueError("Frecuencia invalida")
    return construir_dataset_prophet(puntos, objetivo="precio_promedio_normalizado")


def _a_dataframe(pd, filas: list[ProphetRow]):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def _parametros_backtesting(frecuencia: str, horizonte: int) -> tuple[int, int, int, str]:
    if frecuencia == "mensual":
        return 24, horizonte, horizonte, "MS"
    if frecuencia == "diaria":
        dias = horizonte * 30
        return 180, dias, dias, "D"
    raise ValueError("Frecuencia invalida")


def _evaluar_configuracion(pd, Prophet, config: ConfiguracionExperimento, dataset: list[ProphetRow]) -> ResultadoExperimento:
    min_train_size, test_size, step_size, freq = _parametros_backtesting(config.frecuencia, config.horizonte)
    folds = construir_folds_temporales(dataset, min_train_size=min_train_size, test_size=test_size, step_size=step_size)

    abs_errors: list[float] = []
    apes: list[float] = []
    for fold in folds:
        train_df = _a_dataframe(pd, fold.train)
        test_df = _a_dataframe(pd, fold.test)
        modelo = Prophet(
            stan_backend="CMDSTANPY",
            daily_seasonality=False,
            weekly_seasonality=False,
            yearly_seasonality=config.yearly_seasonality,
            changepoint_prior_scale=config.changepoint_prior_scale,
            seasonality_prior_scale=config.seasonality_prior_scale,
            seasonality_mode=config.seasonality_mode,
        )
        modelo.fit(train_df)
        futuro = modelo.make_future_dataframe(periods=len(test_df), freq=freq)
        forecast = modelo.predict(futuro)[["ds", "yhat"]]
        evaluacion = test_df.merge(forecast, on="ds", how="left")
        evaluacion["abs_error"] = (evaluacion["y"] - evaluacion["yhat"]).abs()
        evaluacion["ape"] = evaluacion["abs_error"] / evaluacion["y"] * 100
        abs_errors.extend(evaluacion["abs_error"].tolist())
        apes.extend(evaluacion["ape"].tolist())

    return ResultadoExperimento(
        frecuencia=config.frecuencia,
        horizonte=config.horizonte,
        yearly_seasonality=config.yearly_seasonality,
        changepoint_prior_scale=config.changepoint_prior_scale,
        seasonality_prior_scale=config.seasonality_prior_scale,
        seasonality_mode=config.seasonality_mode,
        folds=len(folds),
        mae=sum(abs_errors) / len(abs_errors),
        mape=sum(apes) / len(apes),
    )


def _grilla_experimentos() -> list[ConfiguracionExperimento]:
    configuraciones: list[ConfiguracionExperimento] = []
    for frecuencia, horizonte, yearly, cps, sps, modo in product(
        ("mensual", "diaria"),
        (3, 6, 12),
        (False, True),
        (0.01, 0.05),
        (1.0, 10.0),
        ("additive", "multiplicative"),
    ):
        configuraciones.append(
            ConfiguracionExperimento(
                frecuencia=frecuencia,
                horizonte=horizonte,
                yearly_seasonality=yearly,
                changepoint_prior_scale=cps,
                seasonality_prior_scale=sps,
                seasonality_mode=modo,
            )
        )
    return configuraciones


def _guardar_csv(resultados: list[ResultadoExperimento], ruta: Path) -> None:
    lineas = [
        "frecuencia,horizonte,yearly_seasonality,changepoint_prior_scale,seasonality_prior_scale,seasonality_mode,folds,mae,mape"
    ]
    for resultado in resultados:
        lineas.append(
            f"{resultado.frecuencia},{resultado.horizonte},{resultado.yearly_seasonality},"
            f"{resultado.changepoint_prior_scale},{resultado.seasonality_prior_scale},"
            f"{resultado.seasonality_mode},{resultado.folds},{resultado.mae:.4f},{resultado.mape:.4f}"
        )
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias_prophet()
    _configurar_cmdstan(CmdStanPyBackend, IStanBackend)

    registros = _obtener_registros_cemento()
    dataset_por_frecuencia = {
        "mensual": _construir_dataset(registros, "mensual"),
        "diaria": _construir_dataset(registros, "diaria"),
    }

    resultados = [
        _evaluar_configuracion(pd, Prophet, config, dataset_por_frecuencia[config.frecuencia])
        for config in _grilla_experimentos()
    ]
    ranking = sorted(resultados, key=lambda item: item.mae)

    salida = Path("tmp/prophet_cemento_experimentos.csv")
    salida.parent.mkdir(parents=True, exist_ok=True)
    _guardar_csv(ranking, salida)

    print(f"Experimentos evaluados: {len(ranking)}")
    print(f"CSV generado: {salida}")
    print("")
    print("Top 12 configuraciones:")
    for resultado in ranking[:12]:
        print(
            f"- frecuencia={resultado.frecuencia} horizonte={resultado.horizonte} "
            f"yearly={resultado.yearly_seasonality} cps={resultado.changepoint_prior_scale} "
            f"sps={resultado.seasonality_prior_scale} mode={resultado.seasonality_mode} "
            f"MAE={resultado.mae:.2f} MAPE={resultado.mape:.2f}% folds={resultado.folds}"
        )


if __name__ == "__main__":
    main()
