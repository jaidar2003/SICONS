import argparse

from app.modules.auth.infrastructure import models as auth_models  # noqa: F401
from app.modules.catalog.infrastructure.repositories import SQLAlchemyMaterialRepository
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.domain.exceptions import PricingDomainException
from app.modules.pricing.infrastructure.repositories import SQLAlchemyPricingRepository
from app.shared.database.session import SessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Precomputa forecasts de materiales activos.")
    parser.add_argument(
        "--horizontes",
        nargs="+",
        type=int,
        default=[3, 6, 12],
        help="Horizontes en meses a precomputar.",
    )
    parser.add_argument(
        "--legacy-sin-selector",
        action="store_true",
        help="Precomputa forecasts con la firma legacy sin selector de modelo.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    horizontes = tuple(args.horizontes)
    with SessionLocal() as db:
        material_repo = SQLAlchemyMaterialRepository(db)
        pricing_repo = SQLAlchemyPricingRepository(db)
        materiales = material_repo.list_active()

        completados = 0
        saltados = 0
        for material in materiales:
            for horizonte in horizontes:
                try:
                    forecast_material(
                        material,
                        horizonte,
                        pricing_repo,
                        usar_selector_modelo=not args.legacy_sin_selector,
                    )
                    completados += 1
                except PricingDomainException as exc:
                    print(f"Saltando {material.nombre} (H={horizonte}): {exc}")
                    saltados += 1

    print(f"Proceso finalizado. Exitos: {completados} | Saltados: {saltados}")


if __name__ == "__main__":
    main()
