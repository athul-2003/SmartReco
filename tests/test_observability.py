import os

from app.config import Settings
from app.observability import configure_langsmith


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def _clear_env(monkeypatch):
    for prefix in ("LANGSMITH", "LANGCHAIN"):
        for suffix in ("TRACING_V2", "API_KEY", "PROJECT"):
            monkeypatch.delenv(f"{prefix}_{suffix}", raising=False)


def test_configure_langsmith_noop_when_tracing_disabled(monkeypatch):
    _clear_env(monkeypatch)

    configure_langsmith(
        _settings(langchain_tracing_v2=False, langchain_api_key="lsv2_x")
    )

    assert "LANGSMITH_TRACING_V2" not in os.environ
    assert "LANGCHAIN_TRACING_V2" not in os.environ


def test_configure_langsmith_noop_when_api_key_missing(monkeypatch):
    _clear_env(monkeypatch)

    configure_langsmith(_settings(langchain_tracing_v2=True, langchain_api_key=""))

    assert "LANGSMITH_TRACING_V2" not in os.environ


def test_configure_langsmith_sets_both_namespaces_when_fully_configured(monkeypatch):
    _clear_env(monkeypatch)

    configure_langsmith(
        _settings(
            langchain_tracing_v2=True,
            langchain_api_key="lsv2_x",
            langchain_project="my-project",
        )
    )

    for prefix in ("LANGSMITH", "LANGCHAIN"):
        assert os.environ[f"{prefix}_TRACING_V2"] == "true"
        assert os.environ[f"{prefix}_API_KEY"] == "lsv2_x"
        assert os.environ[f"{prefix}_PROJECT"] == "my-project"


def test_configure_langsmith_uses_default_project_when_unset(monkeypatch):
    # Isolate from this developer's local .env (which may itself set
    # LANGCHAIN_PROJECT, e.g. to test against a specific LangSmith
    # project) - this test is specifically about the class-level default.
    _clear_env(monkeypatch)

    configure_langsmith(
        Settings(_env_file=None, langchain_tracing_v2=True, langchain_api_key="lsv2_x")
    )

    assert os.environ["LANGSMITH_PROJECT"] == "smartreco"
    assert os.environ["LANGCHAIN_PROJECT"] == "smartreco"
