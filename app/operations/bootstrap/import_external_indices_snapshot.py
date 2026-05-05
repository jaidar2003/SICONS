import argparse
import pandas as pd
from datetime import date
from decimal import Decimal
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pricing.infrastructure.models import ExternalIndexValue
from app.shared.database.session import SessionLocal

DEFAULT_IPIM_CSV = Path("db/bootstrap/ipim_nivel_general_historico.csv")
IPIM_SERIES_ID = "448.1_NIVEL_GENERAL_0_0_13_46"
SOURCE_NAME = "Snapshot local INDEC"


def import_ipim_snapshot(db: Session, csv_path: Path) -> None:
    if not csv_path.exists():
        print(f"Error: No se encontro el archivo {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["value"] = pd.to_numeric(df["value"])

    inserted = 0
    updated = 0
    unchanged = 0

    for _, row in df.iterrows():
        point_date = row["date"]
        point_value = Decimal(str(row["value"]))

        existing = db.scalar(
            select(ExternalIndexValue).where(
                ExternalIndexValue.series_id == IPIM_SERIES_ID,
                ExternalIndexValue.date == point_date,
            )
        )

        if existing is None:
            db.add(
                ExternalIndexValue(
                    source_name=SOURCE_NAME,
                    series_id=IPIM_SERIES_ID,
                    date=point_date,
                    value=point_value,
                )
            )
            inserted += 1
        else:
            if Decimal(str(existing.value)) != point_value or existing.source_name != SOURCE_NAME:
                existing.value = point_value
                existing.source_name = SOURCE_NAME
                updated += 1
            else:
                unchanged += 1

    db.commit()
    print(f"Importacion de IPIM finalizada: {inserted} insertados, {updated} actualizados, {unchanged} sin cambios.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Importa indices externos desde snapshots locales.")
    parser.add_argument("--ipim-csv", default=str(DEFAULT_IPIM_CSV), help="Ruta al CSV de IPIM.")
    args = parser.parse_args()

    with SessionLocal() as db:
        import_ipim_snapshot(db, Path(args.ipim_csv))


if __name__ == "__main__":
    main()
