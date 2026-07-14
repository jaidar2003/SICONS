from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.auth.domain.exceptions import (
    AuthConflict,
    AuthResourceNotFound,
    InvalidAuthRequest,
    InvalidCredentials,
)
from app.modules.pricing.domain.exceptions import (
    ExternalIndexSyncError,
    ExternalRegressorError,
    ExternalRegressorUnavailableError,
    ForecastRuntimeError,
    ForecastSnapshotRequired,
    InsufficientDataException,
    MaterialNotFoundException,
    PriceImputationError,
    PricingDomainException,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidAuthRequest)
    async def invalid_auth_request_handler(request: Request, exc: InvalidAuthRequest):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(InvalidCredentials)
    async def invalid_credentials_handler(request: Request, exc: InvalidCredentials):
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(AuthResourceNotFound)
    async def auth_not_found_handler(request: Request, exc: AuthResourceNotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(AuthConflict)
    async def auth_conflict_handler(request: Request, exc: AuthConflict):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(ExternalRegressorUnavailableError)
    async def external_regressor_unavailable_handler(request: Request, exc: ExternalRegressorUnavailableError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(ForecastRuntimeError)
    async def forecast_runtime_handler(request: Request, exc: ForecastRuntimeError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(ForecastSnapshotRequired)
    async def forecast_snapshot_required_handler(request: Request, exc: ForecastSnapshotRequired):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

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
