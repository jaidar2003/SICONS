from __future__ import annotations

from datetime import date
from pathlib import Path

import cmdstanpy
from sqlalchemy import select

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.forecasting import ProphetRow, construir_dataset_prophet
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual, construir_serie_precios
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico
from app.shared.database.session import SessionLocal


DEFAULT_DATASET_START = "2022-01-01"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CMDSTAN_VERSION = "cmdstan-2.38.0"


def importar_dependencias_prophet(mensaje_error: str):
    try:
        import pandas as pd
        from prophet import Prophet
        from prophet.models import CmdStanPyBackend, IStanBackend
    except ImportError as exc:
        raise RuntimeError(mensaje_error) from exc
    return pd, Prophet, CmdStanPyBackend, IStanBackend


def configurar_cmdstan(CmdStanPyBackend, IStanBackend, mensaje_error: str) -> None:
    cmdstan_global = Path.home() / ".cmdstan" / CMDSTAN_VERSION
    if not cmdstan_global.exists():
        raise RuntimeError(mensaje_error)

    cmdstanpy.set_cmdstan_path(str(cmdstan_global))

    def fixed_init(self):
        cmdstanpy.set_cmdstan_path(str(cmdstan_global))
        IStanBackend.__init__(self)

    CmdStanPyBackend.__init__ = fixed_init


def obtener_registros_material(nombre_material: str, start: date | None = None) -> tuple[str, list[PrecioSerieInput]]:
    with SessionLocal() as db:
        material = db.scalar(select(Material).where(Material.nombre == nombre_material))
        if material is None:
            raise RuntimeError(f"No existe el material {nombre_material} en la base")

        stmt = (
            select(PrecioHistorico)
            .where(PrecioHistorico.material_id == material.id)
            .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
        )
        if start is not None:
            stmt = stmt.where(PrecioHistorico.fecha >= start)

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
    return material.unidad_base, registros


def construir_dataset_material(
    nombre_material: str,
    *,
    frecuencia: str = "mensual",
    objetivo: str = "precio_promedio_normalizado",
    dataset_start: str | None = None,
) -> list[ProphetRow]:
    start = None
    if dataset_start:
        start = date.fromisoformat(dataset_start)

    _, registros = obtener_registros_material(nombre_material, start=start)
    if frecuencia == "mensual":
        puntos = construir_serie_mensual(registros)
    elif frecuencia == "diaria":
        puntos = construir_serie_precios(registros)
    else:
        raise ValueError("Frecuencia invalida")
    return construir_dataset_prophet(puntos, objetivo=objetivo)


def cargar_dolar_mensual(pd, path_csv: str, columna_salida: str, *, dataset_start: str = DEFAULT_DATASET_START):
    df = pd.read_csv(PROJECT_ROOT / path_csv)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["venta"] = pd.to_numeric(df["venta"], errors="coerce")
    df = df[df["fecha"] >= pd.to_datetime(dataset_start)].copy()
    df["ds"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    return df.groupby("ds", as_index=False)["venta"].mean().rename(columns={"venta": columna_salida})


def cargar_ipc_mensual(pd, path_csv: str, *, dataset_start: str = DEFAULT_DATASET_START):
    df = pd.read_csv(PROJECT_ROOT / path_csv)
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["ipc"] = pd.to_numeric(df["ipc"], errors="coerce")
    df = df[df["fecha"] >= pd.to_datetime(dataset_start)].copy()
    return df.rename(columns={"fecha": "ds"})[["ds", "ipc"]].copy()


def cargar_indice_externo_mensual(
    pd,
    *,
    series_id: str,
    columna_salida: str,
    dataset_start: str = DEFAULT_DATASET_START,
):
    start = date.fromisoformat(dataset_start)
    with SessionLocal() as db:
        stmt = (
            select(ExternalIndexValue)
            .where(
                ExternalIndexValue.series_id == series_id,
                ExternalIndexValue.date >= start,
            )
            .order_by(ExternalIndexValue.date.asc(), ExternalIndexValue.id.asc())
        )
        rows = list(db.scalars(stmt))

    if not rows:
        raise RuntimeError(f"No hay valores del indice externo {series_id} cargados en la base.")

    return pd.DataFrame(
        [
            {
                "ds": pd.to_datetime(value.date),
                columna_salida: float(value.value),
            }
            for value in rows
        ]
    )
