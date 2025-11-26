"""Application entrypoint: sets up FastAPI app, CORS, logging and registers API routers.

This file centralizes server bootstrap concerns (middleware, routers, log levels)
so background services and domain logic stay isolated in their respective modules.
"""
import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import health as health_router
from app.api.routers import jobs as jobs_router
from app.api.routers import resumes as resumes_router
from app.api.routers import match as match_router
from app.api.routers import llm_test as llm_test_router
from app.core.config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific log levels for different modules
logging.getLogger("match.service").setLevel(logging.INFO)
logging.getLogger("match.judge").setLevel(logging.INFO)
logging.getLogger("jobs.pipeline").setLevel(logging.INFO)
logging.getLogger("jobs.chunker").setLevel(logging.INFO)

# Reduce noise from external libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://omniai:3010",      
            "http://omniai-apps:3010", 
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router)
    app.include_router(jobs_router.router)
    app.include_router(resumes_router.router)
    app.include_router(match_router.router)
    app.include_router(llm_test_router.router)

    return app


app = create_app()
