import argparse

from app.modules.pricing.application.forecast_service import precomputar_forecasts_materiales
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    horizontes = tuple(args.horizontes)
    with SessionLocal() as db:
        completados = precomputar_forecasts_materiales(db, horizontes=horizontes)
    print(f"Forecasts precomputados: {len(completados)}")


if __name__ == "__main__":
    main()
