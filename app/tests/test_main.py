import json

import pytest

import main
from main import MemoryStore, create_app


class BrokenStore(MemoryStore):
    def ping(self):
        raise RuntimeError("database down")


@pytest.fixture
def client():
    return create_app(MemoryStore()).test_client()


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_ready_ok(client):
    assert client.get("/ready").status_code == 200


def test_ready_fails_when_store_is_down():
    client = create_app(BrokenStore()).test_client()
    assert client.get("/ready").status_code == 503


def test_version_comes_from_environment(client, monkeypatch):
    monkeypatch.setattr(main, "APP_VERSION", "sha-abc1234")
    assert client.get("/version").get_json() == {"version": "sha-abc1234"}


def test_add_and_list_items(client):
    created = client.post("/items", json={"name": "laptop"})
    assert created.status_code == 201
    assert client.get("/items").get_json() == [{"id": 1, "name": "laptop"}]


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "   "}])
def test_add_item_requires_name(client, body):
    assert client.post("/items", json=body).status_code == 400


def test_metrics_exposes_request_counter(client):
    client.get("/health")
    body = client.get("/metrics").get_data(as_text=True)
    assert "http_requests_total" in body


def test_requests_are_logged_as_json(client, caplog):
    with caplog.at_level("INFO", logger="api"):
        client.get("/items")
    entry = json.loads(caplog.records[-1].getMessage())
    assert entry["event"] == "request"
    assert entry["path"] == "/items"
    assert entry["status"] == 200


def test_debug_endpoint_is_off_by_default(client):
    assert client.get("/debug/error").status_code == 404


def test_debug_endpoint_returns_500_when_enabled():
    app = create_app(MemoryStore(), debug_endpoints=True)
    app.config["PROPAGATE_EXCEPTIONS"] = False
    assert app.test_client().get("/debug/error").status_code == 500
