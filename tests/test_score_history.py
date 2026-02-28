"""Tests for score history SQLite storage."""

import json
import os
import sys

import pytest

# Add api/ to path so we can import db module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))
import db as score_db


@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test_score_history.db")
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    score_db.init_db()


def test_init_db_creates_table(tmp_path, monkeypatch):
    """init_db should create the score_history table without error."""
    db_path = str(tmp_path / "fresh.db")
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    score_db.init_db()
    # Calling twice should also work (IF NOT EXISTS)
    score_db.init_db()


def test_save_and_get_history():
    """save_score should store a record retrievable by get_history."""
    idea = "CLI tool for DNS monitoring"
    row_id = score_db.save_score(
        idea_text=idea,
        score=42,
        breakdown=json.dumps({"reality_signal": 42}),
        keywords=json.dumps(["dns", "monitoring"]),
        depth="quick",
        keyword_source="dictionary",
    )
    assert row_id is not None
    assert row_id > 0

    h = score_db.idea_hash(idea)
    records = score_db.get_history(h)
    assert len(records) == 1
    assert records[0]["score"] == 42
    assert records[0]["idea_text"] == idea
    assert records[0]["depth"] == "quick"


def test_multiple_saves_same_idea():
    """Multiple saves for the same idea should all appear in history."""
    idea = "AI-powered code review tool"
    for score in [30, 45, 60]:
        score_db.save_score(
            idea_text=idea,
            score=score,
            breakdown=json.dumps({"reality_signal": score}),
            keywords=json.dumps(["code", "review"]),
        )

    h = score_db.idea_hash(idea)
    records = score_db.get_history(h)
    assert len(records) == 3
    # Newest first
    scores = [r["score"] for r in records]
    assert 30 in scores
    assert 45 in scores
    assert 60 in scores


def test_idea_hash_case_insensitive():
    """idea_hash should be case-insensitive and strip whitespace."""
    h1 = score_db.idea_hash("DNS Monitoring Tool")
    h2 = score_db.idea_hash("dns monitoring tool")
    h3 = score_db.idea_hash("  DNS Monitoring Tool  ")
    assert h1 == h2
    assert h1 == h3


def test_get_history_empty():
    """get_history should return empty list for unknown hash."""
    records = score_db.get_history("nonexistent_hash_value")
    assert records == []


def test_different_ideas_different_hash():
    """Different ideas should produce different hashes."""
    h1 = score_db.idea_hash("DNS monitoring tool")
    h2 = score_db.idea_hash("Code review automation")
    assert h1 != h2


def test_save_score_returns_incrementing_ids():
    """Each save should return a unique, incrementing row id."""
    ids = []
    for i in range(3):
        row_id = score_db.save_score(
            idea_text=f"idea {i}",
            score=50,
            breakdown="{}",
            keywords="[]",
        )
        ids.append(row_id)
    assert ids[0] < ids[1] < ids[2]
