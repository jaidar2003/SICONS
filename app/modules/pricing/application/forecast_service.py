from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import BEST_PROPHET_CONFIG, construir_dataset_prophet, generar_fechas_mensuales, inicio_mes_siguiente
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual
from app.modules.pricing.infrastructure.forecast_runtime import configurar_cmdstan, importar_dependencias_forecast
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.modules.pricing.infrastructure.regressors import cargar_regresores_mensuales, proyectar_regresores_futuros
from app.modules.pricing.interfaces.schemas import ForecastMetricasRead, ForecastPuntoRead


FORECAST_DATASET_START = date(2022, 1, 1)
FORECAST_MODEL_NAME = "prophet_oficial_ipc_mayorista"
FORECAST_REGRESSOR_NOTE = "Escenario base: dolar oficial, dolar mayorista e IPC futuros proyectados con crecimiento compuesto segun la tendencia de los ultimos 12 meses."


@dataclass(frozen=True)
class ForecastMaterialResult:
    dataset: list
    metricas: ForecastMetricasRead
    forecast: list[ForecastPuntoRead]


def _a_dataframe(pd, filas):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def serie_mensual_material(material: Material, db: Session):
    stmt = (
        select(PrecioHistorico)
        .options(joinedload(PrecioHistorico.fuente))
        .where(
            PrecioHistorico.material_id == material.id,
            PrecioHistorico.fecha >= FORECAST_DATASET_START,
        )
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


def backtesting_forecast(pd, Prophet, dataset, regresores_df, horizonte_meses: int) -> ForecastMetricasRead:
    folds = construir_folds_temporales(dataset, min_train_size=24, test_size=horizonte_meses, step_size=horizonte_meses)
    if not folds:
        raise HTTPException(status_code=422, detail="No hay suficientes datos para evaluar ese horizonte de forecast.")

    abs_errors: list[float] = []
    apes: list[float] = []
    for fold in folds:
        train_df = _a_dataframe(pd, fold.train)
        test_df = _a_dataframe(pd, fold.test)
        full_df = pd.concat([train_df[["ds", "y"]], test_df[["ds", "y"]]], ignore_index=True)
        full_df = full_df.merge(regresores_df, on="ds", how="left")
        for columna in ("dolar_oficial", "dolar_mayorista", "ipc"):
            full_df[columna] = full_df[columna].ffill().bfill()

        modelo = Prophet(stan_backend="CMDSTANPY", **BEST_PROPHET_CONFIG)
        modelo.add_regressor("dolar_oficial")
        modelo.add_regressor("dolar_mayorista")
        modelo.add_regressor("ipc")

        train_reg = full_df.iloc[: len(train_df)][["ds", "y", "dolar_oficial", "dolar_mayorista", "ipc"]].copy()
        futuro = full_df[["ds", "dolar_oficial", "dolar_mayorista", "ipc"]].copy()
        modelo.fit(train_reg)
        forecast = modelo.predict(futuro)[["ds", "yhat"]]

        evaluacion = test_df.merge(forecast, on="ds", how="left")
        evaluacion["abs_error"] = (evaluacion["y"] - evaluacion["yhat"]).abs()
        evaluacion["ape"] = evaluacion["abs_error"] / evaluacion["y"] * 100
        abs_errors.extend(evaluacion["abs_error"].tolist())
        apes.extend(evaluacion["ape"].tolist())

    mae = sum(abs_errors) / len(abs_errors)
    mape = sum(apes) / len(apes)
    return ForecastMetricasRead(
        folds=len(folds),
        mae=Decimal(f"{mae:.2f}"),
        mape=Decimal(f"{mape:.2f}"),
        efectividad_informal=Decimal(f"{100 - mape:.2f}"),
    )


def pronosticar_futuro(pd, Prophet, dataset, regresores_df, horizonte_meses: int, unidad_base: str) -> list[ForecastPuntoRead]:
    dataset_df = _a_dataframe(pd, dataset)
    dataset_reg = dataset_df.merge(regresores_df, on="ds", how="left")
    for columna in ("dolar_oficial", "dolar_mayorista", "ipc"):
        dataset_reg[columna] = dataset_reg[columna].ffill().bfill()

    modelo = Prophet(stan_backend="CMDSTANPY", **BEST_PROPHET_CONFIG)
    modelo.add_regressor("dolar_oficial")
    modelo.add_regressor("dolar_mayorista")
    modelo.add_regressor("ipc")
    modelo.fit(dataset_reg[["ds", "y", "dolar_oficial", "dolar_mayorista", "ipc"]].copy())

    ultima_fecha = dataset[-1].ds
    fechas_futuras = generar_fechas_mensuales(inicio_mes_siguiente(ultima_fecha), horizonte_meses)
    regresores_hasta_ultima_fecha = regresores_df[regresores_df["ds"] <= pd.to_datetime(ultima_fecha)].sort_values("ds")
    if regresores_hasta_ultima_fecha.empty:
        raise HTTPException(status_code=422, detail="No hay regresores externos alineados con la ultima fecha observada.")
    futuro_reg = proyectar_regresores_futuros(pd, regresores_hasta_ultima_fecha, fechas_futuras)
    futuro = pd.concat([dataset_reg[["ds", "dolar_oficial", "dolar_mayorista", "ipc"]], futuro_reg], ignore_index=True)
    forecast = modelo.predict(futuro)[["ds", "yhat"]].tail(horizonte_meses)

    puntos: list[ForecastPuntoRead] = []
    for _, fila in forecast.iterrows():
        precio = float(fila["yhat"])
        equivalencia_25 = Decimal(f"{precio * 25:.2f}") if unidad_base == "kg" else None
        equivalencia_50 = Decimal(f"{precio * 50:.2f}") if unidad_base == "kg" else None
        puntos.append(
            ForecastPuntoRead(
                fecha=fila["ds"].date(),
                precio_proyectado=Decimal(f"{precio:.2f}"),
                precio_equivalente_25kg=equivalencia_25,
                precio_equivalente_50kg=equivalencia_50,
            )
        )
    return puntos


def _forecast_material(
    material: Material,
    horizonte_meses: int,
    pd,
    Prophet,
    db: Session,
) -> ForecastMaterialResult:
    puntos = serie_mensual_material(material, db)
    dataset = construir_dataset_prophet(puntos, objetivo="precio_promedio_normalizado")
    if len(dataset) < 24 + horizonte_meses:
        raise HTTPException(status_code=422, detail=f"No hay suficientes puntos mensuales para generar el forecast de {material.nombre}")

    regresores_df = cargar_regresores_mensuales(pd)
    metricas = backtesting_forecast(pd, Prophet, dataset, regresores_df, horizonte_meses)
    forecast = pronosticar_futuro(pd, Prophet, dataset, regresores_df, horizonte_meses, material.unidad_base)
    return ForecastMaterialResult(dataset=dataset, metricas=metricas, forecast=forecast)


def forecast_material(
    material: Material,
    horizonte_meses: int,
    db: Session,
) -> ForecastMaterialResult:
    cmdstanpy, pd, Prophet, CmdStanPyBackend, IStanBackend = importar_dependencias_forecast()
    configurar_cmdstan(cmdstanpy, CmdStanPyBackend, IStanBackend)
    return _forecast_material(material, horizonte_meses, pd, Prophet, db)
