from pathlib import Path

import cmdstanpy
from sqlalchemy import select

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import ProphetRow, construir_dataset_prophet
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.shared.database.session import SessionLocal


DATASET_START = "2022-01-01"
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
    try:
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise RuntimeError("Faltan dependencias para correr el experimento por horizontes.") from exc
    return pd, Prophet, CmdStanPyBackend, IStanBackend


def _configurar_cmdstan(CmdStanPyBackend, IStanBackend) -> None:
    cmdstan_global = Path.home() / ".cmdstan" / "cmdstan-2.38.0"
    if not cmdstan_global.exists():
        raise RuntimeError("No se encontro CmdStan en ~/.cmdstan/cmdstan-2.38.0.")

    cmdstanpy.set_cmdstan_path(str(cmdstan_global))

    def fixed_init(self):
        cmdstanpy.set_cmdstan_path(str(cmdstan_global))
        IStanBackend.__init__(self)

    CmdStanPyBackend.__init__ = fixed_init


def _obtener_dataset_cemento(pd) -> list[ProphetRow]:
    start = pd.to_datetime(DATASET_START).date()
    with SessionLocal() as db:
        material = db.scalar(select(Material).where(Material.nombre == "Cemento Portland"))
        if material is None:
            raise RuntimeError("No existe el material Cemento Portland en la base")

        stmt = (
            select(PrecioHistorico)
            .where(PrecioHistorico.material_id == material.id, PrecioHistorico.fecha >= start)
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
    puntos = construir_serie_mensual(registros)
    return construir_dataset_prophet(puntos, objetivo="precio_promedio_normalizado")


def _a_dataframe(pd, filas: list[ProphetRow]):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def _cargar_dolar_mensual(pd, path_csv: str, columna_salida: str):
    df = pd.read_csv(path_csv)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["venta"] = pd.to_numeric(df["venta"], errors="coerce")
    df = df[df["fecha"] >= pd.to_datetime(DATASET_START)].copy()
    df["ds"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("ds", as_index=False)["venta"].mean().rename(columns={"venta": columna_salida})


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
