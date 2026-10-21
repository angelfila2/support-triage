import pytest


@pytest.fixture(autouse=True)
def local_test_auth(monkeypatch):
    # API auth itself is exercised by tests which explicitly enable it.
    from backend import auth
    monkeypatch.setattr(auth, "AUTH_REQUIRED", False)

    from backend import audit
    monkeypatch.setattr(audit, "ollama_models", lambda timeout=2: [])
    monkeypatch.setattr(audit, "_manifest_cache", (0, []))
