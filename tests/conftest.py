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
os.environ["CEREBRAS_API_KEY"] = "test-stub-key"
os.environ["SIMULATOR_MODE"] = "auto"
os.environ["ENABLE_PIPELINE_ANALYZER"] = "false"

from src.vialpilot.db.database import Base, engine, init_db  # noqa: E402
from src.vialpilot.api.app import create_app  # noqa: E402
from src.vialpilot.models.schemas import LLMResult  # noqa: E402


@pytest.fixture(autouse=True)
def reset_llm_clients():
    """Reset Cerebras client singleton between tests."""
    import src.vialpilot.llm.client as llm_client

    llm_client._cerebras = None
    yield
    llm_client._cerebras = None


@pytest.fixture(autouse=True)
def stub_gemma4(monkeypatch):
    """Simulate live Gemma 4 responses without calling Cerebras API."""

    def _fake_run_json(self, *, system_prompt, user_prompt, fallback_json, **kwargs):
        return LLMResult(
            mode="real",
            model="gemma-4-31b",
            latency_ms=15.0,
            raw_text=str(fallback_json),
            result_json=fallback_json,
            error=None,
        )

    monkeypatch.setattr(
        "src.vialpilot.llm.cerebras_gemma.CerebrasGemmaClient.run_json",
        _fake_run_json,
    )


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