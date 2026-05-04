from app.experiments.pricing.common import (
    DEFAULT_DATASET_START,
    cargar_dolar_mensual,
    configurar_cmdstan,
    construir_dataset_material,
    importar_dependencias_prophet,
)
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import ProphetRow


DATASET_START = DEFAULT_DATASET_START
OFICIAL_CSV = "tmp/dolares_2022/dolar_oficial_historico.csv"
MAYORISTA_CSV = "tmp/dolares_2022/dolar_mayorista_historico.csv"
HORIZONTES = (3, 6, 12)
BEST_PROPHET_CONFIG = {
    "daily_seasonality": False,
    "weekly_seasonality": False,
    "yearly_seasonality": False,
    "changepoint_prior_scale": 0.01,
    "seasonality_prior_scale": 1.0,
    "seasonality_mode": "additive",
}


def _importar_dependencias():
    return importar_dependencias_prophet("Faltan dependencias para correr el experimento por horizontes.")


def _configurar_cmdstan(CmdStanPyBackend, IStanBackend) -> None:
    configurar_cmdstan(CmdStanPyBackend, IStanBackend, "No se encontro CmdStan en ~/.cmdstan/cmdstan-2.38.0.")


def _obtener_dataset_cemento(pd) -> list[ProphetRow]:
    return construir_dataset_material("Cemento Portland", frecuencia="mensual", objetivo="precio_promedio_normalizado", dataset_start=DATASET_START)


def _a_dataframe(pd, filas: list[ProphetRow]):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def _cargar_dolar_mensual(pd, path_csv: str, columna_salida: str):
    return cargar_dolar_mensual(pd, path_csv, columna_salida, dataset_start=DATASET_START)


def _evaluar_horizonte(pd, Prophet, dataset: list[ProphetRow], regresores_df, horizonte: int) -> tuple[int, int, float, float]:
    folds = construir_folds_temporales(dataset, min_train_size=24, test_size=horizonte, step_size=horizonte)
    abs_errors: list[float] = []
    apes: list[float] = []

    for fold in folds:
        train_df = _a_dataframe(pd, fold.train)
        test_df = _a_dataframe(pd, fold.test)
        full_df = pd.concat([train_df[["ds", "y"]], test_df[["ds", "y"]]], ignore_index=True)
        full_df = full_df.merge(regresores_df, on="ds", how="left")
        for columna in ("dolar_oficial", "dolar_mayorista"):
            full_df[columna] = full_df[columna].ffill().bfill()

        modelo = Prophet(stan_backend="CMDSTANPY", **BEST_PROPHET_CONFIG)
        modelo.add_regressor("dolar_oficial")
        modelo.add_regressor("dolar_mayorista")

        train_reg = full_df.iloc[: len(train_df)][["ds", "y", "dolar_oficial", "dolar_mayorista"]].copy()
        futuro = full_df[["ds", "dolar_oficial", "dolar_mayorista"]].copy()
        modelo.fit(train_reg)
        forecast = modelo.predict(futuro)[["ds", "yhat"]]

        evaluacion = test_df.merge(forecast, on="ds", how="left")
        evaluacion["abs_error"] = (evaluacion["y"] - evaluacion["yhat"]).abs()
        evaluacion["ape"] = evaluacion["abs_error"] / evaluacion["y"] * 100
        abs_errors.extend(evaluacion["abs_error"].tolist())
        apes.extend(evaluacion["ape"].tolist())

    mae = sum(abs_errors) / len(abs_errors)
    mape = sum(apes) / len(apes)
    return horizonte, len(folds), mae, mape


def main() -> None:
    pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias()
    _configurar_cmdstan(CmdStanPyBackend, IStanBackend)

    dataset = _obtener_dataset_cemento(pd)
    oficial = _cargar_dolar_mensual(pd, OFICIAL_CSV, "dolar_oficial")
    mayorista = _cargar_dolar_mensual(pd, MAYORISTA_CSV, "dolar_mayorista")
    regresores = oficial.merge(mayorista, on="ds", how="inner")

    print(f"Dataset cemento desde {DATASET_START}: {len(dataset)} puntos mensuales")
    print("Modelo: prophet_oficial_mayorista")
    print("")

    for horizonte in HORIZONTES:
        horizonte, folds, mae, mape = _evaluar_horizonte(pd, Prophet, dataset, regresores, horizonte)
        efectividad = 100 - mape
        print(
            f"horizonte={horizonte} meses | folds={folds} | "
            f"MAE={mae:.2f} | MAPE={mape:.2f}% | efectividad~={efectividad:.2f}%"
        )


if __name__ == "__main__":
    main()
