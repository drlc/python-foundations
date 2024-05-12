from types import SimpleNamespace

from fastapi import FastAPI


def test_service_is_created():

    # import inside test so env vars monkeypatch is applied first
    from example_app.main import handlers

    assert isinstance(handlers, SimpleNamespace)
    assert isinstance(handlers.api, FastAPI)
