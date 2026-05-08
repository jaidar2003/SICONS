from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


EXPERIMENTS_DIR = Path("tmp/experiments")
OUTPUT_CSV = EXPERIMENTS_DIR / "cemento_forecast_benchmark_master.csv"
SOURCE_GLOB = "cemento_forecast_plateau*.csv"

STD_MAPE_PATTERN = re.compile(r"std_mape_folds=([0-9]+(?:\.[0-9]+)?)")


@dataclass(frozen=True)
class BenchmarkRow:
    nombre_modelo: str
    regresores_features: str
    horizonte_meses: int
    mae: str
    mape: str
    efectividad_informal: str
    folds: int
    std_mape_folds: str
    mejora_vs_baseline: str
    observaciones: str
    estado: str
    source_file: str


def _parse_float(raw: str) -> float | None:
    if raw in {"", "-", "skip"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _derive_effectiveness(mape_raw: str) -> str:
    mape = _parse_float(mape_raw)
    if mape is None:
        return "-"
    return f"{100 - mape:.2f}"


def _extract_std_mape(observaciones: str) -> str:
    match = STD_MAPE_PATTERN.search(observaciones)
    return match.group(1) if match else "-"


def _derive_status(nombre_modelo: str, mejora_vs_baseline: str, observaciones: str, mape_raw: str) -> str:
    if "skip" == mejora_vs_baseline or mape_raw == "-":
        return "omitido"
    if "baseline_obligatorio" in observaciones:
        return "baseline"
    if nombre_modelo == "ensemble_simple_top2":
        return "candidato"

    improvement = _parse_float(mejora_vs_baseline.replace(" pp", ""))
    if improvement is None:
        return "experimental"
    if improvement > 0:
        return "candidato"
    if improvement < 0:
        return "descartado"
    return "experimental"


def _row_priority(source_file: str) -> int:
    priorities = {
        "cemento_forecast_plateau_icc_var_3_6_12.csv": 6,
        "cemento_forecast_plateau_cac_var_3_6_12.csv": 5,
        "cemento_forecast_plateau_cac_var_h3.csv": 4,
        "cemento_forecast_plateau_cac_h3.csv": 3,
        "cemento_forecast_plateau_h3.csv": 2,
        "cemento_forecast_plateau_smoke.csv": 1,
    }
    return priorities.get(source_file, 0)


def _load_rows() -> list[BenchmarkRow]:
    collected: dict[tuple[str, int], BenchmarkRow] = {}
    for path in sorted(EXPERIMENTS_DIR.glob(SOURCE_GLOB)):
        if path.name == OUTPUT_CSV.name:
            continue

        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for raw in reader:
                key = (raw["nombre_modelo"], int(raw["horizonte_meses"]))
                row = BenchmarkRow(
                    nombre_modelo=raw["nombre_modelo"],
                    regresores_features=raw["regresores_features"],
                    horizonte_meses=int(raw["horizonte_meses"]),
                    mae=raw["MAE"],
                    mape=raw["MAPE"],
                    efectividad_informal=_derive_effectiveness(raw["MAPE"]),
                    folds=int(raw["folds"]),
                    std_mape_folds=_extract_std_mape(raw["observaciones"]),
                    mejora_vs_baseline=raw["mejora_vs_baseline"],
                    observaciones=raw["observaciones"],
                    estado=_derive_status(
                        raw["nombre_modelo"],
                        raw["mejora_vs_baseline"],
                        raw["observaciones"],
                        raw["MAPE"],
                    ),
                    source_file=path.name,
                )

                current = collected.get(key)
                if current is None or _row_priority(row.source_file) >= _row_priority(current.source_file):
                    collected[key] = row

    return sorted(
        collected.values(),
        key=lambda item: (
            item.horizonte_meses,
            _parse_float(item.mape) if _parse_float(item.mape) is not None else float("inf"),
            item.nombre_modelo,
        ),
    )


def _write_csv(rows: list[BenchmarkRow]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "nombre_modelo",
                "regresores_features",
                "horizonte_meses",
                "MAE",
                "MAPE",
                "efectividad_informal",
                "folds",
                "std_mape_folds",
                "mejora_vs_baseline",
                "observaciones",
                "estado",
                "source_file",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.nombre_modelo,
                    row.regresores_features,
                    row.horizonte_meses,
                    row.mae,
                    row.mape,
                    row.efectividad_informal,
                    row.folds,
                    row.std_mape_folds,
                    row.mejora_vs_baseline,
                    row.observaciones,
                    row.estado,
                    row.source_file,
                ]
            )


def main() -> None:
    rows = _load_rows()
    _write_csv(rows)
    print(f"Benchmark maestro exportado en: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
