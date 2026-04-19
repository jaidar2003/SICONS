from fastapi import FastAPI

from app.api.routes import fuentes, health, materiales, precios_historicos, presentaciones


def create_app() -> FastAPI:
    app = FastAPI(title="SICONS API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(materiales.router)
    app.include_router(presentaciones.router)
    app.include_router(fuentes.router)
    app.include_router(precios_historicos.router)
    return app


app = create_app()
