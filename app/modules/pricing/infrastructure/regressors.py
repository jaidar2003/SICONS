from datetime import date
from pathlib import Path

from fastapi import HTTPException


PROJECT_ROOT = Path(__file__).resolve().parents[4]
FORECAST_DATASET_START = date(2022, 1, 1)
OFICIAL_CSV = PROJECT_ROOT / "tmp" / "dolares_2022" / "dolar_oficial_historico.csv"
MAYORISTA_CSV = PROJECT_ROOT / "tmp" / "dolares_2022" / "dolar_mayorista_historico.csv"
IPC_CSV = PROJECT_ROOT / "tmp" / "ipc_2022" / "ipc_nacional.csv"
REGRESSOR_TREND_WINDOW_MONTHS = 12


def cargar_regresores_mensuales(pd):
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


def proyectar_regresores_futuros(pd, regresores_historicos, fechas_futuras):
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
