import argparse
from pathlib import Path

import pandas as pd


IPC_XLS_SHEET = "Índices IPC Cobertura Nacional"


def _resolver_input_por_defecto() -> str:
    if Path("data/raw/ipc.xls").exists():
        return "data/raw/ipc.xls"
    return "tmp/ipc_nacional_raw.csv"


def _cargar_ipc_desde_csv(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    columnas_requeridas = {"indice_tiempo", "ipc_nivel_general_nacional"}
    faltantes = columnas_requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(f"Faltan columnas en IPC: {', '.join(sorted(faltantes))}")

    return df.rename(
        columns={
            "indice_tiempo": "fecha",
            "ipc_nivel_general_nacional": "ipc",
        }
    )[["fecha", "ipc"]]


def _cargar_ipc_desde_excel(input_path: Path) -> pd.DataFrame:
    df = pd.read_excel(input_path, sheet_name=IPC_XLS_SHEET, header=None)
    fechas = pd.to_datetime(df.iloc[5, 1:], errors="coerce")
    valores = pd.to_numeric(df.iloc[9, 1:], errors="coerce")
    serie = pd.DataFrame({"fecha": fechas, "ipc": valores}).dropna(subset=["fecha", "ipc"])
    serie["fecha"] = serie["fecha"].dt.to_period("M").dt.to_timestamp()
    if serie.empty:
        raise ValueError("No se pudo extraer la serie de IPC desde el Excel.")
    return serie


def _cargar_ipc(input_path: Path) -> pd.DataFrame:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return _cargar_ipc_desde_csv(input_path)
    if suffix in {".xls", ".xlsx"}:
        return _cargar_ipc_desde_excel(input_path)
    raise ValueError(f"Formato de IPC no soportado: {input_path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normaliza y recorta la serie de IPC nacional.")
    parser.add_argument(
        "--input",
        default=_resolver_input_por_defecto(),
        help="Ruta al archivo crudo de IPC. Soporta CSV de datos.gob.ar o Excel .xls/.xlsx.",
    )
    parser.add_argument(
        "--output",
        default="tmp/ipc_2022/ipc_nacional.csv",
        help="Ruta al CSV limpio de salida.",
    )
    parser.add_argument(
        "--since",
        default="2022-01-01",
        help="Fecha minima inclusive en formato YYYY-MM-DD.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = _cargar_ipc(input_path)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="raise")
    df["fecha"] = df["fecha"].dt.to_period("M").dt.to_timestamp()
    df["ipc"] = pd.to_numeric(df["ipc"], errors="coerce")
    df = df[df["fecha"] >= pd.to_datetime(args.since)].copy()
    df = df.sort_values("fecha").reset_index(drop=True)
    df["fecha"] = df["fecha"].dt.strftime("%Y-%m-%d")
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Filas exportadas: {len(df)}")
    print(f"Desde: {df.iloc[0]['fecha']}")
    print(f"Hasta: {df.iloc[-1]['fecha']}")
    print(f"Fuente: {input_path}")
    print(f"CSV: {output_path}")


if __name__ == "__main__":
    main()
