from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = PROJECT_ROOT / "data" / "raw" / "icc.xls"
OUTPUT_PATH = PROJECT_ROOT / "tmp" / "dataset_icc_buildwise.xlsx"

MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


class LocalIccAdapter:
    def __init__(self, file_path: Path):
        self.file_path = file_path

    @staticmethod
    def _clean_numeric(value):
        if pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(".", "").replace(",", ".")
        if not text or text.lower() == "nan":
            return None

        return pd.to_numeric(text, errors="coerce")

    @staticmethod
    def _build_period(year_value, month_value):
        if pd.isna(year_value) or pd.isna(month_value):
            return None

        month_text = str(month_value).replace("*", "").strip().lower()
        month_number = MONTHS_ES.get(month_text)
        if month_number is None:
            return None

        return pd.Timestamp(year=int(year_value), month=month_number, day=1)

    def get_historical_data(self, start_date: str = "2022-01-01") -> pd.DataFrame:
        try:
            raw = pd.read_excel(
                self.file_path,
                sheet_name="Nivel general y capítulos_ind",
                header=None,
            )

            years = raw.iloc[3]
            months = raw.iloc[4]
            label_to_row = {
                "Nivel general": None,
                "Materiales": None,
                "Mano de obra (1)": None,
            }

            for idx, value in raw.iloc[:, 0].items():
                if value in label_to_row:
                    label_to_row[value] = idx

            if any(index is None for index in label_to_row.values()):
                raise ValueError("No se encontraron las filas esperadas en la planilla ICC.")

            records = []
            current_year = None

            for col in range(1, raw.shape[1]):
                if pd.notna(years.iloc[col]):
                    current_year = years.iloc[col]

                period = self._build_period(current_year, months.iloc[col])
                if period is None:
                    continue

                records.append(
                    {
                        "period": period,
                        "general": self._clean_numeric(raw.iloc[label_to_row["Nivel general"], col]),
                        "materials": self._clean_numeric(raw.iloc[label_to_row["Materiales"], col]),
                        "labour_force": self._clean_numeric(raw.iloc[label_to_row["Mano de obra (1)"], col]),
                    }
                )

            df = pd.DataFrame(records).dropna(subset=["period", "general"]).sort_values("period")
            df["var_general"] = df["general"].pct_change() * 100
            df["var_materials"] = df["materials"].pct_change() * 100
            df["var_labour"] = df["labour_force"].pct_change() * 100

            df = df[df["period"] >= pd.Timestamp(start_date)].reset_index(drop=True)
            return df.fillna(0)

        except Exception as e:
            print(f"Error procesando el Excel local: {e}")
            return pd.DataFrame()


def main() -> None:
    adapter = LocalIccAdapter(INPUT_PATH)
    data = adapter.get_historical_data("2022-01-01")

    if data.empty:
        print("No se pudo procesar el archivo. Verificá el nombre y la ruta.")
        return

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    pd.set_option("display.float_format", "{:.2f}".format)

    print("--- VARIACIONES MENSUALES ICC DESDE ENERO 2022 ---")
    print(data[["period", "var_general", "var_materials", "var_labour"]])
    print(f"\nTotal de registros: {len(data)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        data.to_excel(OUTPUT_PATH, index=False)
        print(f"\nArchivo Excel generado en: {OUTPUT_PATH.resolve()}")
    except ImportError:
        print("\nNo se pudo generar el archivo .xlsx porque falta openpyxl.")
        print("Instalalo con: .venv/bin/python -m pip install openpyxl")


if __name__ == "__main__":
    main()
