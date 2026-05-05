from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.pricing.domain.exceptions import ExternalIndexSyncError
from app.modules.pricing.infrastructure.datos_argentina_client import DatosArgentinaClientError, fetch_series
from app.modules.pricing.infrastructure.models import ExternalIndexValue


@dataclass(frozen=True)
class ExternalIndexSyncResult:
    source_name: str
    series_id: str
    inserted: int
    updated: int
    unchanged: int


def sync_external_index(
    db: Session,
    *,
    series_id: str,
    source_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ExternalIndexSyncResult:
    try:
        points = fetch_series(series_id, start_date=start_date, end_date=end_date)
    except DatosArgentinaClientError as exc:
        raise ExternalIndexSyncError(str(exc)) from exc

    inserted = 0
    updated = 0
    unchanged = 0
    for point in points:
        existing = db.scalar(
            select(ExternalIndexValue).where(
                ExternalIndexValue.series_id == series_id,
                ExternalIndexValue.date == point.date,
            )
        )
        if existing is None:
            db.add(
                ExternalIndexValue(
                    source_name=source_name,
                    series_id=series_id,
                    date=point.date,
                    value=point.value,
                )
            )
            inserted += 1
            continue

        changed = existing.source_name != source_name or Decimal(existing.value) != point.value
        if not changed:
            unchanged += 1
            continue
        existing.source_name = source_name
        existing.value = point.value
        updated += 1

    db.commit()
    return ExternalIndexSyncResult(
        source_name=source_name,
        series_id=series_id,
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
    )


def list_external_indices(
    db: Session,
    *,
    series_id: str | None = None,
    source_name: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ExternalIndexValue]:
    stmt = select(ExternalIndexValue).order_by(ExternalIndexValue.date.asc(), ExternalIndexValue.id.asc())
    if series_id is not None:
        stmt = stmt.where(ExternalIndexValue.series_id == series_id)
    if source_name is not None:
        stmt = stmt.where(ExternalIndexValue.source_name == source_name)
    if start_date is not None:
        stmt = stmt.where(ExternalIndexValue.date >= start_date)
    if end_date is not None:
        stmt = stmt.where(ExternalIndexValue.date <= end_date)
    return list(db.scalars(stmt))
