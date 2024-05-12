import pytest


@pytest.fixture(scope="session")
def monkeypatch_session():
    from _pytest.monkeypatch import MonkeyPatch

    m = MonkeyPatch()
    yield m
    m.undo()


@pytest.fixture(scope="session", autouse=True)
def configs_env(monkeypatch_session: pytest.MonkeyPatch):
    monkeypatch_session.setenv("SERVICE_NAME", "service")
    monkeypatch_session.setenv("ENV", "test")
    monkeypatch_session.setenv("LOG_LEVEL", "ERROR")
    monkeypatch_session.setenv("SERVICE_VERSION", "tv")
    monkeypatch_session.setenv("WEBAPP_VERSION", "tv")
    monkeypatch_session.setenv("WEBAPP_TITLE", "Service title")
    monkeypatch_session.setenv(
        "STORE_CONNECTION_CLASS_NAME", "base.common.adapters.stores.PostgresConnection"
    )
    monkeypatch_session.setenv(
        "STORE_CONNECTION_CLASS_NAME_SETTINGS", "base.common.settings.PostgresConnectionSettings"
    )
    monkeypatch_session.setenv("POSTGRES_USER", "local-user")
    monkeypatch_session.setenv("POSTGRES_PASSWORD", "local-pwd")
    monkeypatch_session.setenv("POSTGRES_DB", "local-database")
    monkeypatch_session.setenv("POSTGRES_SCHEMA", "account")
    monkeypatch_session.setenv("POSTGRES_HOST", "localhost")
    monkeypatch_session.setenv("POSTGRES_PORT", "5430")
    monkeypatch_session.setenv("ADMIN_AUTH_ID", "tokenauthid")
    monkeypatch_session.setenv("EXAMPLE_GATEWAY_URL", "http://example-gateway")
    monkeypatch_session.setenv("ACCOUNT_ID", "account-id")
