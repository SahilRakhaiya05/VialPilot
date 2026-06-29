"""Pytest fixtures with isolated test database."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["VIALPILOT_SKIP_LOCAL_ENV"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="vialpilot_test_")
os.environ["GEMINI_API_KEY"] = ""
os.environ["CEREBRAS_API_KEY"] = ""
os.environ["SIMULATOR_MODE"] = "auto"
os.environ["ENABLE_PIPELINE_ANALYZER"] = "false"

from src.vialpilot.db.database import Base, engine, init_db  # noqa: E402
from src.vialpilot.api.app import create_app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_llm_clients():
    """Ensure tests never use production API keys cached in LLM singletons."""
    import src.vialpilot.llm.client as llm_client

    llm_client._cerebras = None
    llm_client._gemini = None
    yield
    llm_client._cerebras = None
    llm_client._gemini = None


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def upload_dir() -> Path:
    return Path(os.environ["UPLOAD_DIR"])