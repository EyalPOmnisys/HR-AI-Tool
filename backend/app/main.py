from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.base import Base, engine
from app.api.routers import jobs as jobs_router
from app.api.routers import health as health_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")

    # DB init (MVP)
    Base.metadata.create_all(bind=engine)

    # CORS – allow local frontend dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router.router)
    app.include_router(jobs_router.router)

    return app


app = create_app()
