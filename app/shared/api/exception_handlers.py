from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.pricing.domain.exceptions import (
    ExternalIndexSyncError,
    ExternalRegressorError,
    InsufficientDataException,
    MaterialNotFoundException,
    PriceImputationError,
    PricingDomainException,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(MaterialNotFoundException)
    async def material_not_found_handler(request: Request, exc: MaterialNotFoundException):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InsufficientDataException)
    async def insufficient_data_handler(request: Request, exc: InsufficientDataException):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ExternalRegressorError)
    async def external_regressor_handler(request: Request, exc: ExternalRegressorError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ExternalIndexSyncError)
    async def external_index_sync_handler(request: Request, exc: ExternalIndexSyncError):
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PriceImputationError)
    async def price_imputation_handler(request: Request, exc: PriceImputationError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(PricingDomainException)
    async def pricing_domain_handler(request: Request, exc: PricingDomainException):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )
