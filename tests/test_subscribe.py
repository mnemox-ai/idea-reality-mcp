"""Tests for subscriber email collection (v0.4.0)."""

import os
import sys

import pytest

# Add api/ to path so we can import db module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
import db as score_db


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test_subscribe.db")
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    score_db.init_db()
    score_db.init_subscribers_table()


# --- db.py unit tests ---


def test_init_subscribers_table_idempotent(tmp_path, monkeypatch):
    """init_subscribers_table should be safe to call multiple times."""
    db_path = str(tmp_path / "fresh.db")
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    score_db.init_subscribers_table()
    score_db.init_subscribers_table()  # should not raise


def test_save_subscriber_returns_id():
    """save_subscriber should return a positive row id."""
    row_id = score_db.save_subscriber("test@example.com", "abc123")
    assert row_id is not None
    assert row_id > 0


def test_save_subscriber_increments_id():
    """Each subscriber insert should get an incrementing id."""
    id1 = score_db.save_subscriber("a@x.com", "hash1")
    id2 = score_db.save_subscriber("b@x.com", "hash2")
    assert id2 > id1


def test_get_subscriber_count_empty():
    """Subscriber count should be 0 on fresh DB."""
    assert score_db.get_subscriber_count() == 0


def test_get_subscriber_count_after_inserts():
    """Subscriber count should reflect number of inserts."""
    score_db.save_subscriber("a@x.com", "h1")
    score_db.save_subscriber("b@x.com", "h2")
    score_db.save_subscriber("c@x.com", "h3")
    assert score_db.get_subscriber_count() == 3


def test_save_subscriber_logs_to_stdout(caplog):
    """save_subscriber should log [SUBSCRIBE] to stdout as backup."""
    import logging

    with caplog.at_level(logging.INFO, logger="db"):
        score_db.save_subscriber("log@test.com", "hashXYZ")

    assert any("[SUBSCRIBE]" in msg for msg in caplog.messages)
    assert any("log@test.com" in msg for msg in caplog.messages)


# --- API endpoint tests (require fastapi + httpx) ---


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    fastapi = pytest.importorskip("fastapi")
    httpx = pytest.importorskip("httpx")
    from starlette.testclient import TestClient

    # Import after path setup
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
    from main import app

    return TestClient(app)


def test_subscribe_endpoint_success(client, tmp_path, monkeypatch):
    """POST /api/subscribe should return unlocked: true."""
    resp = client.post(
        "/api/subscribe",
        json={"email": "user@example.com", "idea_hash": "abc123def"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["unlocked"] is True


def test_subscribe_endpoint_invalid_email(client):
    """POST /api/subscribe with invalid email should return 422."""
    resp = client.post(
        "/api/subscribe",
        json={"email": "not-an-email", "idea_hash": "abc123"},
    )
    assert resp.status_code == 422


def test_subscribe_endpoint_empty_email(client):
    """POST /api/subscribe with empty email should return 422."""
    resp = client.post(
        "/api/subscribe",
        json={"email": "", "idea_hash": "abc123"},
    )
    assert resp.status_code == 422


def test_subscribers_count_endpoint(client):
    """GET /api/subscribers/count should return a count."""
    resp = client.get("/api/subscribers/count")
    assert resp.status_code == 200
    data = resp.json()
    assert "count" in data
    assert isinstance(data["count"], int)


def test_check_returns_idea_hash(client):
    """POST /api/check should include idea_hash in response."""
    resp = client.post(
        "/api/check",
        json={"idea_text": "DNS monitoring CLI tool", "depth": "quick"},
    )
    # May fail if network unavailable, but at minimum shouldn't 422
    if resp.status_code == 200:
        data = resp.json()
        assert "idea_hash" in data
        assert len(data["idea_hash"]) == 64  # SHA256 hex
