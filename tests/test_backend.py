"""Pengujian API, sesi, dan SQLite untuk backend CurryCoach."""
import pytest
from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret",
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "ADMIN_KEY": "test-admin",
    })
    return app.test_client()


def test_health_and_themes(client):
    assert client.get("/api/health").get_json()["status"] == "ok"
    data = client.get("/api/themes").get_json()
    assert data["themes"][0]["id"] == "currycoach"


def test_api_chat_stores_two_messages(client):
    response = client.post("/api/chat", json={"theme": "currycoach", "message": "halo"})
    assert response.status_code == 200
    assert response.get_json()["intent"] == "sapaan"
    history = client.get("/api/history/currycoach").get_json()["messages"]
    assert [item["sender"] for item in history] == ["user", "bot"]


def test_explain_returns_candidates(client):
    response = client.post("/api/explain", json={"message": "cara shooting"})
    data = response.get_json()
    assert response.status_code == 200
    assert data["candidates"]
    assert data["threshold"] == 0.45
    assert "details" in data["candidates"][0]


def test_history_isolated_between_sessions(client):
    client.post("/api/chat", json={"message": "halo"})
    first = client.get("/api/history/currycoach").get_json()
    other = client.application.test_client()
    second = other.get("/api/history/currycoach").get_json()
    assert first["count"] == 2
    assert second["count"] == 0


def test_delete_history_only_deletes_current_session(client):
    client.post("/api/chat", json={"message": "halo"})
    response = client.delete("/api/history/currycoach")
    assert response.status_code == 200
    assert response.get_json()["deleted"] == 2
    assert client.get("/api/history/currycoach").get_json()["count"] == 0


def test_stats_require_admin_key(client):
    assert client.get("/api/stats/currycoach").status_code == 401
    response = client.get("/api/stats/currycoach", headers={"X-Admin-Key": "test-admin"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_questions"] == 0
    assert "intent_stats" in data


def test_invalid_payloads(client):
    assert client.post("/api/chat", json={}).status_code == 400
    assert client.post("/api/chat", json={"message": "x" * 301}).status_code == 413
    assert client.post("/api/chat", data="not json").status_code == 400


def test_wrong_theme_returns_404(client):
    assert client.get("/api/history/not-real").status_code == 404
    assert client.post("/api/chat", json={"theme": "not-real", "message": "halo"}).status_code == 404
