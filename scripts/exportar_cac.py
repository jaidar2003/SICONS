from pathlib import Path

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
OUTPUT_PATH = PROJECT_ROOT / "tmp" / "dataset_cac_buildwise.xlsx"
BASE_URL = "https://hchsrnyrgtdqqholoksg.supabase.co/rest/v1/CAC_INDEX"


def load_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()

    return values


class MiObraCacAdapter:
    def __init__(self, api_key: str, token: str):
        self.url = BASE_URL
        # Si el token ya viene con 'Bearer ', no lo duplicamos
        auth_header = token if token.startswith("Bearer ") else f"Bearer {token}"
        self.headers = {
            "apikey": api_key,
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def get_historical_data(self, start_date: str = "2022-01-01") -> pd.DataFrame:
        params = {
            "select": "period,general,materials,labour_force",
            "order": "period.asc",
        }

        try:
            response = requests.get(self.url, headers=self.headers, params=params, timeout=30)

            if response.status_code != 200:
                print(f"Error {response.status_code}: {response.text}")
                return pd.DataFrame()

            df = pd.DataFrame(response.json())
            df["period"] = pd.to_datetime(df["period"])
            df["general"] = pd.to_numeric(df["general"])
            df["materials"] = pd.to_numeric(df["materials"])
            df["labour_force"] = pd.to_numeric(df["labour_force"])

            df["var_general"] = df["general"].pct_change() * 100
            df["var_materials"] = df["materials"].pct_change() * 100
            df["var_labour"] = df["labour_force"].pct_change() * 100

            df_filtered = df[df["period"] >= pd.Timestamp(start_date)].reset_index(drop=True)
            return df_filtered.fillna(0)

        except Exception as e:
            print(f"Error crítico en la conexión: {e}")
            return pd.DataFrame()


def main() -> None:
    env = load_env_file(ENV_PATH)
    api_key = env.get("SUPABASE_CAC_API_KEY")
    bearer_token = env.get("SUPABASE_CAC_BEARER_TOKEN")

    if not api_key or not bearer_token:
        print("Faltan SUPABASE_CAC_API_KEY o SUPABASE_CAC_BEARER_TOKEN en .env")
        return

    adapter = MiObraCacAdapter(api_key=api_key, token=bearer_token)
    data = adapter.get_historical_data("2022-01-01")

    if data.empty:
        print("No se encontraron datos para procesar.")
        return

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    pd.set_option("display.float_format", "{:.2f}".format)

    print("\n" + "=" * 80)
    print("SISTEMA SICONS: DATASET HISTÓRICO CAC (CON VARIACIONES)")
    print("=" * 80)
    print(data[["period", "var_general", "var_materials", "var_labour"]])

    print("\n" + "=" * 80)
    print("RESUMEN DE PROMEDIOS MENSUALES (DESDE 2022)")
    print(f"Variación General Promedio: {data['var_general'].mean():.2f}%")
    print(f"Variación Materiales Promedio: {data['var_materials'].mean():.2f}%")
    print(f"Variación Mano de Obra Promedio: {data['var_labour'].mean():.2f}%")
    print("=" * 80)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data.to_excel(OUTPUT_PATH, index=False)
        print(f"\nArchivo Excel generado en: {OUTPUT_PATH.resolve()}")
    except ImportError:
        print("\nNo se pudo generar el archivo .xlsx porque falta openpyxl.")
        print("Instalalo con: .venv/bin/python -m pip install openpyxl")


if __name__ == "__main__":
    main()
