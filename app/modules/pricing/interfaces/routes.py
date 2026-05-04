from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import require_admin
from app.modules.pricing.application.backtesting import construir_folds_temporales
from app.modules.pricing.application.forecasting import BEST_PROPHET_CONFIG, construir_dataset_prophet, generar_fechas_mensuales, inicio_mes_siguiente
from app.modules.pricing.application.priorities import MaterialPriorityInput, priorizar_materiales_criticos
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios
from app.modules.pricing.domain.rules import calcular_precio_normalizado
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.modules.pricing.interfaces.schemas import (
    ForecastMetricasRead,
    ForecastPuntoRead,
    ForecastResponseRead,
    MaterialCriticidadCreate,
    MaterialCriticidadRead,
    MaterialCriticidadResponseRead,
    PrecioHistoricoCreate,
    PrecioHistoricoRangoRead,
    PrecioHistoricoRead,
    PuntoSeriePrecioRead,
)
from app.shared.database.session import get_db


router = APIRouter(tags=["precios historicos"])
PROJECT_ROOT = Path(__file__).resolve().parents[4]
FORECAST_DATASET_START = date(2022, 1, 1)
OFICIAL_CSV = PROJECT_ROOT / "tmp" / "dolares_2022" / "dolar_oficial_historico.csv"
MAYORISTA_CSV = PROJECT_ROOT / "tmp" / "dolares_2022" / "dolar_mayorista_historico.csv"
IPC_CSV = PROJECT_ROOT / "tmp" / "ipc_2022" / "ipc_nacional.csv"
FORECAST_MODEL_NAME = "prophet_oficial_ipc_mayorista"
FORECAST_REGRESSOR_NOTE = "Escenario base: dolar oficial, dolar mayorista e IPC futuros proyectados con crecimiento compuesto segun la tendencia de los ultimos 12 meses."
REGRESSOR_TREND_WINDOW_MONTHS = 12


def _importar_dependencias_forecast():
    try:
        import cmdstanpy
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Faltan dependencias para generar el forecast.") from exc
    return cmdstanpy, pd, Prophet, CmdStanPyBackend, IStanBackend


def _configurar_cmdstan(cmdstanpy, CmdStanPyBackend, IStanBackend) -> None:
    cmdstan_global = Path.home() / ".cmdstan" / "cmdstan-2.38.0"
    if not cmdstan_global.exists():
        raise HTTPException(status_code=500, detail="No se encontro CmdStan para correr Prophet.")

    cmdstanpy.set_cmdstan_path(str(cmdstan_global))

    def fixed_init(self):
        cmdstanpy.set_cmdstan_path(str(cmdstan_global))
        IStanBackend.__init__(self)

    CmdStanPyBackend.__init__ = fixed_init


def _a_dataframe(pd, filas):
    return pd.DataFrame([{"ds": pd.to_datetime(fila.ds), "y": fila.y} for fila in filas])


def _cargar_regresores_mensuales(pd):
    if not OFICIAL_CSV.exists() or not MAYORISTA_CSV.exists() or not IPC_CSV.exists():
        raise HTTPException(status_code=500, detail="No se encontraron los CSV de regresores externos.")

    def cargar(path: Path, columna: str):
        df = pd.read_csv(path)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["venta"] = pd.to_numeric(df["venta"], errors="coerce")
        df = df[df["fecha"] >= pd.to_datetime(FORECAST_DATASET_START)].copy()
        df["ds"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
        return df.groupby("ds", as_index=False)["venta"].mean().rename(columns={"venta": columna})

    def cargar_ipc(path: Path):
        df = pd.read_csv(path)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df["ipc"] = pd.to_numeric(df["ipc"], errors="coerce")
        df = df[df["fecha"] >= pd.to_datetime(FORECAST_DATASET_START)].copy()
        return df.rename(columns={"fecha": "ds"})[["ds", "ipc"]]

    oficial = cargar(OFICIAL_CSV, "dolar_oficial")
    mayorista = cargar(MAYORISTA_CSV, "dolar_mayorista")
    ipc = cargar_ipc(IPC_CSV)
    return oficial.merge(mayorista, on="ds", how="inner").merge(ipc, on="ds", how="inner")


def _proyectar_regresores_futuros(pd, regresores_historicos, fechas_futuras):
    historial = regresores_historicos.sort_values("ds").tail(REGRESSOR_TREND_WINDOW_MONTHS).copy()
    if historial.empty:
        raise HTTPException(status_code=422, detail="No hay historial suficiente de regresores externos para proyectar el forecast.")

    futuros = {"ds": pd.to_datetime(fechas_futuras)}
    periodos = max(len(historial) - 1, 1)

    for columna in ("dolar_oficial", "dolar_mayorista", "ipc"):
        valores = historial[columna].dropna().tolist()
        if not valores:
            raise HTTPException(status_code=422, detail=f"No hay datos del regresor {columna} para proyectar el forecast.")

        ultimo_valor = float(valores[-1])
        primer_valor = float(valores[0])
        tasa_mensual = 0.0 if primer_valor <= 0 else (ultimo_valor / primer_valor) ** (1 / periodos) - 1
        futuros[columna] = [
            ultimo_valor * ((1 + tasa_mensual) ** paso)
            for paso in range(1, len(fechas_futuras) + 1)
        ]

    return pd.DataFrame(futuros)


def _serie_mensual_material(material: Material, db: Session):
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


def _backtesting_forecast(pd, Prophet, dataset, regresores_df, horizonte_meses: int) -> ForecastMetricasRead:
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


def _pronosticar_futuro(pd, Prophet, dataset, regresores_df, horizonte_meses: int, unidad_base: str) -> list[ForecastPuntoRead]:
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
    futuro_reg = _proyectar_regresores_futuros(pd, regresores_hasta_ultima_fecha, fechas_futuras)
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
) -> tuple[list, ForecastMetricasRead, list[ForecastPuntoRead]]:
    puntos = _serie_mensual_material(material, db)
    dataset = construir_dataset_prophet(puntos, objetivo="precio_promedio_normalizado")
    if len(dataset) < 24 + horizonte_meses:
        raise HTTPException(status_code=422, detail=f"No hay suficientes puntos mensuales para generar el forecast de {material.nombre}")

    regresores_df = _cargar_regresores_mensuales(pd)
    metricas = _backtesting_forecast(pd, Prophet, dataset, regresores_df, horizonte_meses)
    forecast = _pronosticar_futuro(pd, Prophet, dataset, regresores_df, horizonte_meses, material.unidad_base)
    return dataset, metricas, forecast


@router.get("/precios-historicos/rango", response_model=PrecioHistoricoRangoRead)
def obtener_rango_precios_historicos(db: Session = Depends(get_db)) -> PrecioHistoricoRangoRead:
    hoy = date.today()
    desde, hasta_real = db.execute(
        select(func.min(PrecioHistorico.fecha), func.max(PrecioHistorico.fecha))
    ).one()
    hasta = min(hasta_real, hoy) if hasta_real is not None else None
    return PrecioHistoricoRangoRead(
        desde=desde,
        hasta=hasta,
        hoy=hoy,
        tiene_fechas_futuras=hasta_real is not None and hasta_real > hoy,
        hasta_real=hasta_real,
    )


@router.get("/precios-historicos", response_model=list[PrecioHistoricoRead])
def listar_precios_historicos(
    material_id: int | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    stmt = select(PrecioHistorico).order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    if material_id is not None:
        stmt = stmt.where(PrecioHistorico.material_id == material_id)
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)
    return list(db.scalars(stmt))


@router.get("/materiales/{material_id}/precios", response_model=list[PrecioHistoricoRead])
def listar_precios_por_material(
    material_id: int,
    db: Session = Depends(get_db),
) -> list[PrecioHistorico]:
    if db.get(Material, material_id) is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    stmt = (
        select(PrecioHistorico)
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.desc(), PrecioHistorico.id.desc())
    )
    return list(db.scalars(stmt))


@router.get("/materiales/{material_id}/serie-precios", response_model=list[PuntoSeriePrecioRead])
def obtener_serie_precios_material(
    material_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    agrupacion: str = "dia",
    db: Session = Depends(get_db),
):
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    stmt = (
        select(PrecioHistorico)
        .options(joinedload(PrecioHistorico.fuente))
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
    )
    if desde is not None:
        stmt = stmt.where(PrecioHistorico.fecha >= desde)
    if hasta is not None:
        stmt = stmt.where(PrecioHistorico.fecha <= hasta)

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
    if agrupacion == "mensual":
        return construir_serie_mensual(registros)
    if agrupacion != "dia":
        raise HTTPException(status_code=422, detail="La agrupacion debe ser 'dia' o 'mensual'")
    return construir_serie_precios(registros)


@router.get("/materiales/{material_id}/forecast", response_model=ForecastResponseRead)
def obtener_forecast_material(
    material_id: int,
    horizonte_meses: int = 3,
    db: Session = Depends(get_db),
) -> ForecastResponseRead:
    if horizonte_meses < 1 or horizonte_meses > 12:
        raise HTTPException(status_code=422, detail="El horizonte_meses debe estar entre 1 y 12")

    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    cmdstanpy, pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias_forecast()
    _configurar_cmdstan(cmdstanpy, CmdStanPyBackend, IStanBackend)
    dataset, metricas, forecast = _forecast_material(material, horizonte_meses, pd, Prophet, db)

    return ForecastResponseRead(
        material_id=material.id,
        material_nombre=material.nombre,
        unidad_base=material.unidad_base,
        horizonte_meses=horizonte_meses,
        modelo=FORECAST_MODEL_NAME,
        supuesto_regresores=FORECAST_REGRESSOR_NOTE,
        ultima_fecha_observada=dataset[-1].ds,
        ultimo_precio_observado=Decimal(f"{dataset[-1].y:.2f}"),
        metricas=metricas,
        puntos=forecast,
    )


@router.post("/materiales/criticidad", response_model=MaterialCriticidadResponseRead)
def priorizar_materiales_por_criticidad(
    payload: MaterialCriticidadCreate,
    db: Session = Depends(get_db),
) -> MaterialCriticidadResponseRead:
    if payload.alpha == 0 and payload.beta == 0:
        raise HTTPException(status_code=422, detail="alpha y beta no pueden ser ambos cero")

    cmdstanpy, pd, Prophet, CmdStanPyBackend, IStanBackend = _importar_dependencias_forecast()
    _configurar_cmdstan(cmdstanpy, CmdStanPyBackend, IStanBackend)

    materiales_prioridad: list[MaterialPriorityInput] = []
    for item in payload.materiales:
        material = db.get(Material, item.material_id)
        if material is None:
            raise HTTPException(status_code=404, detail=f"Material no encontrado: {item.material_id}")

        dataset, _, forecast = _forecast_material(material, payload.horizonte_meses, pd, Prophet, db)
        punto_objetivo = forecast[-1]
        materiales_prioridad.append(
            MaterialPriorityInput(
                material_id=material.id,
                material_nombre=material.nombre,
                unidad_base=material.unidad_base,
                cantidad_requerida=item.cantidad_requerida,
                precio_actual_normalizado=Decimal(f"{dataset[-1].y:.2f}"),
                precio_proyectado_normalizado=punto_objetivo.precio_proyectado,
            )
        )

    ranking = priorizar_materiales_criticos(materiales_prioridad, alpha=payload.alpha, beta=payload.beta)
    return MaterialCriticidadResponseRead(
        horizonte_meses=payload.horizonte_meses,
        alpha=payload.alpha,
        beta=payload.beta,
        materiales=[MaterialCriticidadRead(**resultado.__dict__) for resultado in ranking],
    )


@router.post("/precios-historicos", response_model=PrecioHistoricoRead, status_code=status.HTTP_201_CREATED)
def crear_precio_historico(
    payload: PrecioHistoricoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> PrecioHistorico:
    if payload.fecha > date.today():
        raise HTTPException(status_code=422, detail="La fecha no puede ser futura")

    material = db.get(Material, payload.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")

    precio_normalizado = payload.precio_original
    if payload.presentacion_id is not None:
        presentacion = db.get(Presentacion, payload.presentacion_id)
        if presentacion is None:
            raise HTTPException(status_code=404, detail="Presentacion no encontrada")
        if presentacion.material_id != payload.material_id:
            raise HTTPException(status_code=422, detail="La presentacion no pertenece al material")
        precio_normalizado = calcular_precio_normalizado(payload.precio_original, Decimal(presentacion.cantidad_base))

    if payload.fuente_id is not None and db.get(Fuente, payload.fuente_id) is None:
        raise HTTPException(status_code=404, detail="Fuente no encontrada")

    precio = PrecioHistorico(
        **payload.model_dump(),
        precio_normalizado=precio_normalizado,
    )
    db.add(precio)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="El precio historico ya existe") from exc
    db.refresh(precio)
    return precio
