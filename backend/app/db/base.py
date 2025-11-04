# path: backend/app/db/base.py
# Purpose: SQLAlchemy engine, session factory, and declarative base. Single source of DB truth.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from . import session as _session  # just for get_db typing
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # proactively validate connections
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Yield a database session; close it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
