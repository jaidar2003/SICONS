import argparse
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure import models as catalog_models  # noqa: F401
from app.modules.pricing.infrastructure.models import ExternalIndexValue
from app.shared.database.session import SessionLocal

DEFAULT_IPIM_CSV = Path("db/bootstrap/ipim_nivel_general_historico.csv")
DEFAULT_ICC_CSV = Path("tmp/experiments/icc_historico.csv")
DEFAULT_CAC_CSV = Path("tmp/experiments/cac_historico.csv")

IPIM_SERIES_ID = "448.1_NIVEL_GENERAL_0_0_13_46"
ICC_SERIES_IDS = {
    "general": "ICC_NIVEL_GENERAL",
    "materials": "ICC_MATERIALES",
    "labour_force": "ICC_MANO_DE_OBRA",
    "var_general": "ICC_VAR_GENERAL",
    "var_materials": "ICC_VAR_MATERIALES",
    "var_labour": "ICC_VAR_MANO_DE_OBRA",
}
CAC_SERIES_IDS = {
    "general": "CAC_GENERAL",
    "materials": "CAC_MATERIALES",
    "labour_force": "CAC_MANO_DE_OBRA",
    "var_general": "CAC_VAR_GENERAL",
    "var_materials": "CAC_VAR_MATERIALES",
    "var_labour": "CAC_VAR_MANO_DE_OBRA",
}
SOURCE_NAMES = {
    "ipim": "Snapshot local INDEC",
    "icc": "Snapshot local ICC",
    "cac": "Snapshot local CAC",
}


def _upsert_snapshot_series(
    db: Session,
    *,
    df: pd.DataFrame,
    series_id: str,
    source_name: str,
    date_column: str,
    value_column: str,
) -> tuple[int, int, int]:
    if date_column not in df.columns or value_column not in df.columns:
        return 0, 0, 0

    df = df[[date_column, value_column]].copy()
    df[date_column] = pd.to_datetime(df[date_column]).dt.date
    df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
    df = df.dropna(subset=[date_column, value_column]).copy()

    inserted = 0
    updated = 0
    unchanged = 0

    for _, row in df.iterrows():
        point_date = row[date_column]
        point_value = Decimal(str(row[value_column]))

        existing = db.scalar(
            select(ExternalIndexValue).where(
                ExternalIndexValue.series_id == series_id,
                ExternalIndexValue.date == point_date,
            )
        )

        if existing is None:
            db.add(
                ExternalIndexValue(
                    source_name=source_name,
                    series_id=series_id,
                    date=point_date,
                    value=point_value,
                )
            )
            inserted += 1
            continue

        if Decimal(str(existing.value)) != point_value or existing.source_name != source_name:
            existing.value = point_value
            existing.source_name = source_name
            updated += 1
        else:
            unchanged += 1

    return inserted, updated, unchanged


def import_ipim_snapshot(db: Session, csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"Error: No se encontro el archivo {csv_path}")
        return

    df = pd.read_csv(csv_path)
    inserted, updated, unchanged = _upsert_snapshot_series(
        db,
        df=df,
        series_id=IPIM_SERIES_ID,
        source_name=SOURCE_NAMES["ipim"],
        date_column="date",
        value_column="value",
    )
    db.commit()
    print(f"Importacion de IPIM finalizada: {inserted} insertados, {updated} actualizados, {unchanged} sin cambios.")


def import_icc_snapshot(db: Session, csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"Error: No se encontro el archivo {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if "period" not in df.columns:
        print(f"Error: {csv_path} no contiene la columna 'period'.")
        return

    df["date"] = pd.to_datetime(df["period"]).dt.date

    total_inserted = 0
    total_updated = 0
    total_unchanged = 0

    for column, series_id in ICC_SERIES_IDS.items():
        if column not in df.columns:
            continue
        inserted, updated, unchanged = _upsert_snapshot_series(
            db,
            df=df,
            series_id=series_id,
            source_name=SOURCE_NAMES["icc"],
            date_column="date",
            value_column=column,
        )
        total_inserted += inserted
        total_updated += updated
        total_unchanged += unchanged

    db.commit()
    print(
        "Importacion de ICC finalizada: "
        f"{total_inserted} insertados, {total_updated} actualizados, {total_unchanged} sin cambios."
    )


def import_cac_snapshot(db: Session, csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"Error: No se encontro el archivo {csv_path}")
        return

    df = pd.read_csv(csv_path)
    if "period" not in df.columns:
        print(f"Error: {csv_path} no contiene la columna 'period'.")
        return

    df["date"] = pd.to_datetime(df["period"]).dt.date

    total_inserted = 0
    total_updated = 0
    total_unchanged = 0

    for column, series_id in CAC_SERIES_IDS.items():
        if column not in df.columns:
            continue
        inserted, updated, unchanged = _upsert_snapshot_series(
            db,
            df=df,
            series_id=series_id,
            source_name=SOURCE_NAMES["cac"],
            date_column="date",
            value_column=column,
        )
        total_inserted += inserted
        total_updated += updated
        total_unchanged += unchanged

    db.commit()
    print(
        "Importacion de CAC finalizada: "
        f"{total_inserted} insertados, {total_updated} actualizados, {total_unchanged} sin cambios."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa indices externos desde snapshots locales.")
    parser.add_argument("--ipim-csv", default=str(DEFAULT_IPIM_CSV), help="Ruta al CSV de IPIM.")
    parser.add_argument("--icc-csv", default=str(DEFAULT_ICC_CSV), help="Ruta al CSV de ICC.")
    parser.add_argument("--cac-csv", default=str(DEFAULT_CAC_CSV), help="Ruta al CSV de CAC.")
    args = parser.parse_args()

    with SessionLocal() as db:
        import_ipim_snapshot(db, Path(args.ipim_csv))
        import_icc_snapshot(db, Path(args.icc_csv))
        import_cac_snapshot(db, Path(args.cac_csv))


if __name__ == "__main__":
    main()
