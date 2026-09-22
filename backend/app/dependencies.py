from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.ml_runtime import ModelRuntime


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_model_runtime(request: Request) -> ModelRuntime:
    return request.app.state.model_runtime
