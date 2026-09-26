"""FastAPI composition root for Synapse-CRS v0.1."""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from synapse_contracts.version import API_VERSION

from synapse_api.config import get_settings
from synapse_api.errors import register_exception_handlers
from synapse_api.routers import audit, cases, health, targets

logger = logging.getLogger("synapse.api")

DESCRIPTION = """
Synapse-CRS v0.1 is a fail-closed control-plane foundation.

It registers owned targets, records explicit authorization, stores case
pipeline state, and appends audit events. It does not discover
vulnerabilities, exploit systems, patch binaries, or apply runtime
mitigations. Transitioning a case into ACTION only updates stored state.
""".strip()


def _reject_migration_credentials() -> None:
    """The API process must not be able to read the migration role's DSN."""
    if os.environ.get("MIGRATION_DATABASE_URL"):
        raise RuntimeError(
            "Refusing to start the API while MIGRATION_DATABASE_URL is set. "
            "Run migrations in a separate process."
        )


def create_app() -> FastAPI:
    _reject_migration_credentials()
    settings = get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    docs_url = None if settings.synapse_environment == "production" else "/docs"
    redoc_url = None if settings.synapse_environment == "production" else "/redoc"
    app = FastAPI(
        title="Synapse-CRS API",
        version=API_VERSION,
        description=DESCRIPTION,
        docs_url=docs_url,
        redoc_url=redoc_url,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(targets.router)
    app.include_router(cases.router)
    app.include_router(audit.router)

    @app.get("/", include_in_schema=False)
    def root() -> dict[str, str]:
        return {
            "service": "synapse-crs-api",
            "version": API_VERSION,
            "health": "/health",
            "ready": "/ready",
            "docs": docs_url or "",
            "summary": (
                "v0.1 records authorization, case state, and audit events. "
                "It does not execute security actions."
            ),
        }

    logger.info("synapse-crs api configured environment=%s", settings.synapse_environment)
    return app


class _LazyASGIApp:
    """Build the FastAPI app on first use so imports do not require secrets."""

    def __init__(self) -> None:
        self._app: FastAPI | None = None

    def _get(self) -> FastAPI:
        if self._app is None:
            self._app = create_app()
        return self._app

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        app = self._get()
        await app(scope, receive, send)


app = _LazyASGIApp()
