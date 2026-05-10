from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.auth.interfaces import routes as auth
from app.modules.catalog.interfaces import fuentes, materiales, presentaciones
from app.modules.health.interfaces import routes as health
from app.modules.pricing.interfaces import routes as precios_historicos
from app.shared.api.exception_handlers import register_exception_handlers
from app.shared.config.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(title="BuildWise API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(materiales.router)
    app.include_router(presentaciones.router)
    app.include_router(fuentes.router)
    app.include_router(precios_historicos.router)
    return app


app = create_app()
