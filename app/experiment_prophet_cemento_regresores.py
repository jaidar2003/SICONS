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


DATASET_START = "2022-01-01"
BLUE_CSV = "tmp/dolares_2022/dolar_blue_historico.csv"
OFICIAL_CSV = "tmp/dolares_2022/dolar_oficial_historico.csv"
MAYORISTA_CSV = "tmp/dolares_2022/dolar_mayorista_historico.csv"
IPC_CSV = "tmp/ipc_2022/ipc_nacional.csv"
BEST_PROPHET_CONFIG = {
    "daily_seasonality": False,
    "weekly_seasonality": False,
    "yearly_seasonality": False,
    "changepoint_prior_scale": 0.01,
    "seasonality_prior_scale": 1.0,
    "seasonality_mode": "additive",
}


@dataclass(frozen=True)
class ResultadoModelo:
    nombre: str
    mae: float
    mape: float


def _importar_dependencias():
    try:
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise RuntimeError("Faltan dependencias para correr el experimento con regresores.") from exc
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


def _cargar_ipc_mensual(pd):
    df = pd.read_csv(IPC_CSV)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["ipc"] = pd.to_numeric(df["ipc"], errors="coerce")
    df = df[df["fecha"] >= pd.to_datetime(DATASET_START)].copy()
    df = df.rename(columns={"fecha": "ds"})
    return df[["ds", "ipc"]].copy()


def _combinar_regresores(base_df, otros_df):
    combinado = base_df.copy()
    for df in otros_df:
        combinado = combinado.merge(df, on="ds", how="inner")
    return combinado


def _calcular_metricas(evaluacion_df) -> tuple[float, float]:
    mae = float(evaluacion_df["abs_error"].mean())
    mape = float(evaluacion_df["ape"].mean())
    return mae, mape


def _evaluar_prophet(pd, Prophet, train: list[ProphetRow], test: list[ProphetRow], regresores_df=None, columnas_regresoras=None, nombre="prophet"):
    train_df = _a_dataframe(pd, train)
    test_df = _a_dataframe(pd, test)
    modelo = Prophet(stan_backend="CMDSTANPY", **BEST_PROPHET_CONFIG)

    if regresores_df is None:
        modelo.fit(train_df)
        futuro = modelo.make_future_dataframe(periods=len(test_df), freq="MS")
        forecast = modelo.predict(futuro)[["ds", "yhat"]]
    else:
        columnas_regresoras = columnas_regresoras or []
        full_df = pd.concat([train_df[["ds", "y"]], test_df[["ds", "y"]]], ignore_index=True)
        full_df = full_df.merge(regresores_df, on="ds", how="left")
        for columna in columnas_regresoras:
            full_df[columna] = full_df[columna].ffill().bfill()
            modelo.add_regressor(columna)

        train_reg = full_df.iloc[: len(train_df)][["ds", "y", *columnas_regresoras]].copy()
        futuro = full_df[["ds", *columnas_regresoras]].copy()
        modelo.fit(train_reg)
        forecast = modelo.predict(futuro)[["ds", "yhat"]]

    evaluacion = test_df.merge(forecast, on="ds", how="left")
    evaluacion["abs_error"] = (evaluacion["y"] - evaluacion["yhat"]).abs()
    evaluacion["ape"] = evaluacion["abs_error"] / evaluacion["y"] * 100
    mae, mape = _calcular_metricas(evaluacion)
    return ResultadoModelo(nombre, mae, mape)


def main() -> None:
    pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias()
    _configurar_cmdstan(CmdStanPyBackend, IStanBackend)

    dataset = _obtener_dataset_cemento(pd)
    blue = _cargar_dolar_mensual(pd, BLUE_CSV, "dolar_blue")
    oficial = _cargar_dolar_mensual(pd, OFICIAL_CSV, "dolar_oficial")
    mayorista = _cargar_dolar_mensual(pd, MAYORISTA_CSV, "dolar_mayorista")
    ipc = _cargar_ipc_mensual(pd)
    folds = construir_folds_temporales(dataset, min_train_size=24, test_size=3, step_size=3)

    configuraciones = {
        "prophet_base": {"regresores_df": None, "columnas": []},
        "prophet_blue": {"regresores_df": blue, "columnas": ["dolar_blue"]},
        "prophet_oficial": {"regresores_df": oficial, "columnas": ["dolar_oficial"]},
        "prophet_mayorista": {"regresores_df": mayorista, "columnas": ["dolar_mayorista"]},
        "prophet_ipc": {"regresores_df": ipc, "columnas": ["ipc"]},
        "prophet_blue_ipc": {
            "regresores_df": _combinar_regresores(blue, [ipc]),
            "columnas": ["dolar_blue", "ipc"],
        },
        "prophet_oficial_ipc": {
            "regresores_df": _combinar_regresores(oficial, [ipc]),
            "columnas": ["dolar_oficial", "ipc"],
        },
        "prophet_mayorista_ipc": {
            "regresores_df": _combinar_regresores(mayorista, [ipc]),
            "columnas": ["dolar_mayorista", "ipc"],
        },
        "prophet_oficial_blue": {
            "regresores_df": _combinar_regresores(oficial, [blue]),
            "columnas": ["dolar_oficial", "dolar_blue"],
        },
        "prophet_oficial_mayorista": {
            "regresores_df": _combinar_regresores(oficial, [mayorista]),
            "columnas": ["dolar_oficial", "dolar_mayorista"],
        },
        "prophet_oficial_ipc_blue": {
            "regresores_df": _combinar_regresores(oficial, [ipc, blue]),
            "columnas": ["dolar_oficial", "ipc", "dolar_blue"],
        },
        "prophet_oficial_ipc_mayorista": {
            "regresores_df": _combinar_regresores(oficial, [ipc, mayorista]),
            "columnas": ["dolar_oficial", "ipc", "dolar_mayorista"],
        },
    }
    acumulado = {nombre: [] for nombre in configuraciones}

    for fold in folds:
        for nombre, config in configuraciones.items():
            acumulado[nombre].append(
                _evaluar_prophet(
                    pd,
                    Prophet,
                    fold.train,
                    fold.test,
                    regresores_df=config["regresores_df"],
                    columnas_regresoras=config["columnas"],
                    nombre=nombre,
                )
            )

    print(f"Dataset cemento desde {DATASET_START}: {len(dataset)} puntos mensuales")
    print(f"Folds: {len(folds)}")
    print("")
    ranking = []
    for nombre, resultados in acumulado.items():
        mae = sum(item.mae for item in resultados) / len(resultados)
        mape = sum(item.mape for item in resultados) / len(resultados)
        ranking.append((nombre, mae, mape))
    for nombre, mae, mape in sorted(ranking, key=lambda item: item[1]):
        print(f"{nombre}: MAE={mae:.2f} | MAPE={mape:.2f}%")


if __name__ == "__main__":
    main()
