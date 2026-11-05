"""Liveness and readiness. Neither endpoint returns configuration or rows."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from synapse_contracts.version import API_VERSION

from synapse_api.db import get_db
from synapse_api.errors import ApiError

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "synapse-crs-api", "version": API_VERSION}


@router.get("/ready")
def ready(session: Session = Depends(get_db)) -> dict[str, str]:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise ApiError(
            503,
            "database_unavailable",
            "PostgreSQL is not reachable.",
        ) from None
    return {"status": "ready", "database": "ok", "version": API_VERSION}
