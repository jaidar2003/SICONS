from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.data_quality.cement_invoice_dates import CONFIRMED_INVOICE_DATES
from app.shared.database.audit_service import register_audit_log
from app.shared.database.session import SessionLocal

EXPECTED_OLD_DATE = date(2026, 11, 26)
EXPECTED_SOURCE = "Factura compra"
EXPECTED_MATERIAL = "Cemento Portland"
EXPECTED_PRESENTATION = "Bolsa 25 kg"
EXPECTED_ORIGIN = "REAL"
CONFIRMATION = "CORREGIR-FECHAS-CEMENTO-2025"


@dataclass(frozen=True)
class CorrectionEvidence:
    record_id: int
    invoice: str
    source: str
    material: str
    presentation: str
    old_date: date
    new_date: date
    original_price: Decimal
    normalized_price: Decimal
    currency: str
    origin: str
    created_at: datetime
    status: str


def load_evidence(db: Session) -> list[CorrectionEvidence]:
    statement = (
        select(PrecioHistorico, Fuente, Material, Presentacion)
        .join(Fuente, PrecioHistorico.fuente_id == Fuente.id)
        .join(Material, PrecioHistorico.material_id == Material.id)
        .join(Presentacion, PrecioHistorico.presentacion_id == Presentacion.id)
        .where(PrecioHistorico.numero_comprobante.in_(CONFIRMED_INVOICE_DATES))
        .order_by(PrecioHistorico.numero_comprobante)
    )
    rows = list(db.execute(statement))
    found_invoices = [price.numero_comprobante for price, _, _, _ in rows]
    if found_invoices != sorted(CONFIRMED_INVOICE_DATES):
        raise RuntimeError(
            "La operacion requiere exactamente los comprobantes confirmados. "
            f"Encontrados: {found_invoices!r}."
        )

    evidence: list[CorrectionEvidence] = []
    for price, source, material, presentation in rows:
        invoice = price.numero_comprobante or ""
        new_date = CONFIRMED_INVOICE_DATES[invoice]
        if source.nombre != EXPECTED_SOURCE:
            raise RuntimeError(f"Fuente inesperada para {invoice}: {source.nombre!r}")
        if material.nombre != EXPECTED_MATERIAL:
            raise RuntimeError(f"Material inesperado para {invoice}: {material.nombre!r}")
        if presentation.nombre_presentacion != EXPECTED_PRESENTATION:
            raise RuntimeError(f"Presentacion inesperada para {invoice}: {presentation.nombre_presentacion!r}")
        if price.origen_dato != EXPECTED_ORIGIN:
            raise RuntimeError(f"Origen inesperado para {invoice}: {price.origen_dato!r}")
        if price.fecha not in (EXPECTED_OLD_DATE, new_date):
            raise RuntimeError(f"Fecha inesperada para {invoice}: {price.fecha.isoformat()}")
        if price.precio_original <= 0 or price.precio_normalizado <= 0:
            raise RuntimeError(f"Precio invalido para {invoice}")

        evidence.append(
            CorrectionEvidence(
                record_id=price.id,
                invoice=invoice,
                source=source.nombre,
                material=material.nombre,
                presentation=presentation.nombre_presentacion,
                old_date=price.fecha,
                new_date=new_date,
                original_price=Decimal(price.precio_original),
                normalized_price=Decimal(price.precio_normalizado),
                currency=price.moneda,
                origin=price.origen_dato,
                created_at=price.created_at,
                status="unchanged" if price.fecha == new_date else "pending",
            )
        )
    return evidence


def correct_records(db: Session, *, apply: bool) -> list[CorrectionEvidence]:
    evidence = load_evidence(db)
    if not apply:
        return evidence

    for item in evidence:
        if item.status == "unchanged":
            continue
        price = db.get(PrecioHistorico, item.record_id)
        if price is None or price.fecha != EXPECTED_OLD_DATE:
            raise RuntimeError(f"El registro {item.record_id} cambio durante la operacion")
        price.fecha = item.new_date
        register_audit_log(
            db,
            usuario_id=None,
            accion="DATA_QUALITY_CORRECTED",
            recurso="PrecioHistorico",
            recurso_id=str(item.record_id),
            cambios={
                "numero_comprobante": item.invoice,
                "campo": "fecha",
                "valor_anterior": item.old_date.isoformat(),
                "valor_nuevo": item.new_date.isoformat(),
                "motivo": "error de carga confirmado contra comprobante original",
            },
        )
    db.commit()
    return evidence


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Corrige las fechas confirmadas de dos comprobantes de Cemento Portland. Dry-run por defecto."
    )
    parser.add_argument("--apply", action="store_true", help="Aplica y audita la correccion.")
    parser.add_argument("--confirm", help=f"Confirmacion requerida al aplicar: {CONFIRMATION}")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.apply and args.confirm != CONFIRMATION:
        raise SystemExit(f"Para aplicar use --apply --confirm {CONFIRMATION}")

    with SessionLocal() as db:
        evidence = correct_records(db, apply=args.apply)
        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"Modo: {mode}")
        for item in evidence:
            print(
                f"id={item.record_id} comprobante={item.invoice} fuente={item.source!r} "
                f"fecha={item.old_date.isoformat()} -> {item.new_date.isoformat()} "
                f"precio={item.original_price} {item.currency} presentacion={item.presentation!r} "
                f"creado={item.created_at.isoformat()} estado={item.status}"
            )


if __name__ == "__main__":
    main()
