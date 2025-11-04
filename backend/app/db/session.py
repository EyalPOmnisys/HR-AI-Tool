# path: backend/app/db/session.py
# Purpose: Keep a dedicated module for typing/consistency if extended later.
# Notes: Kept minimal—imported by other modules if needed for type hints.
from sqlalchemy.orm import Session  # re-export for convenience

__all__ = ["Session"]