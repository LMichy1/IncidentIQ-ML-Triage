import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.main import create_app
from app.ml_runtime import ModelRuntime


@pytest.fixture()
def test_engine():
    # StaticPool: a single shared connection, so the in-memory DB survives
    # across the multiple connections SQLAlchemy would otherwise open (each
    # of which would see a blank ":memory:" database of its own).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(test_engine, monkeypatch):
    """A fully wired app: real trained artifact, in-memory SQLite. This
    exercises the real inference path end-to-end, not a mocked model."""
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    import app.dependencies as deps

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def client_no_model(test_engine, monkeypatch):
    """App wired the same way, but the model artifact points somewhere
    nonexistent — exercises the "model unavailable" failure path."""
    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    import app.dependencies as deps
    import app.main as main_module
    from pathlib import Path as _Path

    def override_get_db():
        session = TestSession()
        try:
            yield session
        finally:
            session.close()

    original_runtime_cls = main_module.ModelRuntime

    class BrokenModelRuntime(ModelRuntime):
        def __init__(self):
            super().__init__(artifact_dir=_Path("/nonexistent/artifact/dir"))

    monkeypatch.setattr(main_module, "ModelRuntime", BrokenModelRuntime)

    app = main_module.create_app()
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    monkeypatch.setattr(main_module, "ModelRuntime", original_runtime_cls)
