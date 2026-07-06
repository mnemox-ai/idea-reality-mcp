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
    # Force the semantic-search matrix to reload every call so the in-memory cache
    # never leaks one test's embeddings into another's fresh DB.
    monkeypatch.setattr(score_db, "_EMB_CACHE_TTL", 0.0, raising=False)
    score_db.invalidate_embedding_cache()
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


# ---------------------------------------------------------------------------
# Semantic embeddings (P1)
# ---------------------------------------------------------------------------

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from api.embeddings import pack_embedding, unpack_embedding  # noqa: E402


def _unit(seed):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(1536).astype(np.float32)
    return (x / np.linalg.norm(x)).tolist()


def test_pack_unpack_roundtrip():
    v = [0.1, -0.2, 0.3, 0.0]
    assert np.allclose(unpack_embedding(pack_embedding(v)), v, atol=1e-6)
    assert unpack_embedding(b"") == []


def test_embedding_column_added_to_legacy_table(tmp_path, monkeypatch):
    """init_db must ALTER-in the embedding column on a pre-embedding table."""
    import sqlite3

    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE score_history (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "idea_hash TEXT, idea_text TEXT, score INT, breakdown TEXT, keywords TEXT, "
        "depth TEXT, lang TEXT, keyword_source TEXT, created_at TEXT)"
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    score_db.init_db()
    cols = {r[1] for r in sqlite3.connect(db_path).execute("PRAGMA table_info(score_history)").fetchall()}
    assert "embedding" in cols


def test_semantic_search_ranks_paraphrase_first():
    base = np.asarray(_unit(1), dtype=np.float32)
    para = base * 0.9 + np.asarray(_unit(2), dtype=np.float32) * 0.1
    para = (para / np.linalg.norm(para)).tolist()
    far = _unit(99)

    score_db.save_score("split bills with roommates", 71, "{}", "[]", embedding=pack_embedding(base.tolist()))
    score_db.save_score("a photo editing tool", 55, "{}", "[]", embedding=pack_embedding(far))

    res = score_db.search_similar_by_embedding(para, limit=5)
    assert res, "expected at least one match"
    assert res[0]["idea_text"] == "split bills with roommates"
    assert res[0]["similarity"] > res[-1]["similarity"]


def test_rows_missing_embedding_and_backfill_flow():
    rid = score_db.save_score("idea without vector", 60, "{}", "[]")
    missing_ids = [r["id"] for r in score_db.rows_missing_embedding()]
    assert rid in missing_ids
    score_db.set_embedding(rid, pack_embedding(_unit(7)))
    assert rid not in [r["id"] for r in score_db.rows_missing_embedding()]


def test_semantic_search_empty_corpus_and_zero_vector():
    assert score_db.search_similar_by_embedding(_unit(1)) == []  # nothing embedded yet
    score_db.save_score("something", 50, "{}", "[]", embedding=pack_embedding(_unit(3)))
    assert score_db.search_similar_by_embedding([0.0] * 1536) == []  # zero query -> []
