from pathlib import Path

import pytest

from core.settings import Settings, get_settings


@pytest.fixture(autouse=True)
def isolate_llm_settings(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.setenv("MATCH_MODEL", "")
    monkeypatch.setenv("JOB_SEARCH_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        data_dir=tmp_path / "data",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        checkpoint_url=f"sqlite:///{tmp_path / 'checkpoints.db'}",
        llm_api_key="",
        allow_heuristic_fallback=True,
    )
