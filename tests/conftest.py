import pytest
import requests


@pytest.fixture(autouse=True)
def isolate_external_services(monkeypatch, tmp_path):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("CACHE_ADMIN_PASSWORD", raising=False)

    def no_network(*args, **kwargs):
        raise AssertionError("Unit tests must not access external services")

    monkeypatch.setattr(requests, "get", no_network)
    monkeypatch.setattr(requests, "post", no_network)
