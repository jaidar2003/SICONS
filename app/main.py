from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, fuentes, health, materiales, precios_historicos, presentaciones


def create_app() -> FastAPI:
    app = FastAPI(title="SICONS API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(materiales.router)
    app.include_router(presentaciones.router)
    app.include_router(fuentes.router)
    app.include_router(precios_historicos.router)
    return app


app = create_app()
