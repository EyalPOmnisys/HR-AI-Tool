from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health as health_router
from app.api.routers import jobs as jobs_router
from app.api.routers import resumes as resumes_router
from app.core.config import settings

def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router)
    app.include_router(jobs_router.router)
    app.include_router(resumes_router.router)

    return app

app = create_app()
