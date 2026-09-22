"""FastAPI app factory. Startup loads exactly one pinned model artifact
explicitly — never trains, never retrains, never picks "latest" implicitly.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import init_db
from app.errors import IncidentNotFoundError, ModelUnavailableError
from app.ml_runtime import ModelRuntime
from app.routes.health import router as health_router
from app.routes.incidents import router as incidents_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("incidentiq")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    runtime = ModelRuntime()
    runtime.load()
    if not runtime.is_loaded:
        logger.error(
            "Starting with NO model loaded (%s). /ready will report 503 and "
            "incident submission will fail until this is fixed.",
            runtime.load_error,
        )
    app.state.model_runtime = runtime
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="IncidentIQ API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(incidents_router)

    @app.exception_handler(IncidentNotFoundError)
    def _not_found(request: Request, exc: IncidentNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error_code": "incident_not_found", "detail": str(exc)},
        )

    @app.exception_handler(ModelUnavailableError)
    def _model_unavailable(request: Request, exc: ModelUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"error_code": "model_unavailable", "detail": str(exc)},
        )

    return app


app = create_app()
