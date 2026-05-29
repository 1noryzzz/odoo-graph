import pytest


@pytest.fixture(autouse=True)
def _disable_telemetry_by_default(monkeypatch):
    monkeypatch.setenv("ODOO_GRAPH_TELEMETRY", "0")
