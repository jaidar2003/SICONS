import argparse
import json
from pathlib import Path

import pandas as pd


TIPOS_PRIORIZADOS = ("blue", "oficial", "mayorista")


def _cargar_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError("El JSON de dolares debe contener una lista de registros")
    return data


def _normalizar_dataframe(data: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(data)
    columnas_requeridas = {"casa", "compra", "venta", "fecha"}
    faltantes = columnas_requeridas.difference(df.columns)
    if faltantes:
        faltantes_str = ", ".join(sorted(faltantes))
        raise ValueError(f"Faltan columnas requeridas en el JSON: {faltantes_str}")

    df = df.copy()
    df["casa"] = df["casa"].astype(str).str.strip().str.lower()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="raise")
    df["compra"] = pd.to_numeric(df["compra"], errors="coerce")
    df["venta"] = pd.to_numeric(df["venta"], errors="coerce")
    df = df.sort_values(["casa", "fecha"]).reset_index(drop=True)
    return df


def _exportar_dataframe(df: pd.DataFrame, path: Path) -> None:
    salida = df.copy()
    salida["fecha"] = salida["fecha"].dt.strftime("%Y-%m-%d")
    salida.to_csv(path, index=False, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta historicos de dolares desde JSON a CSV.")
    parser.add_argument(
        "--input",
        default="dolares_historico.json",
        help="Ruta al JSON historico descargado desde la API.",
    )
    parser.add_argument(
        "--output-dir",
        default="tmp/dolares",
        help="Directorio donde se guardaran los CSV exportados.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Fecha minima inclusive en formato YYYY-MM-DD para filtrar la exportacion.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = _cargar_json(input_path)
    df = _normalizar_dataframe(data)
    if args.since:
        since = pd.to_datetime(args.since, errors="raise")
        df = df[df["fecha"] >= since].copy()

    _exportar_dataframe(df, output_dir / "dolares_historico.csv")

    casas = sorted(df["casa"].unique())
    for casa in casas:
        sub = df[df["casa"] == casa].copy()
        _exportar_dataframe(sub, output_dir / f"dolar_{casa}_historico.csv")

    print(f"Registros totales: {len(df)}")
    print(f"Casas exportadas: {', '.join(casas)}")
    print(f"CSV general: {output_dir / 'dolares_historico.csv'}")
    print("")
    print("Resumen por casa:")
    for casa in TIPOS_PRIORIZADOS:
        sub = df[df["casa"] == casa]
        if sub.empty:
            print(f"- {casa}: sin registros")
            continue
        desde = sub["fecha"].min().strftime("%Y-%m-%d")
        hasta = sub["fecha"].max().strftime("%Y-%m-%d")
        print(
            f"- {casa}: {len(sub)} filas | desde={desde} hasta={hasta} | "
            f"csv={output_dir / f'dolar_{casa}_historico.csv'}"
        )


if __name__ == "__main__":
    main()
