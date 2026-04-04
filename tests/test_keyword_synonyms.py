"""Tests for keyword synonym expansion."""

from idea_reality_mcp.scoring.synonyms import KEYWORD_SYNONYMS


class TestKeywordSynonyms:
    def test_todo_has_synonyms(self):
        assert "todo" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["todo"]
        assert "task manager" in syns
        assert len(syns) >= 2

    def test_expense_has_synonyms(self):
        assert "expense" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["expense"]
        assert "budget tracker" in syns

    def test_chat_has_synonyms(self):
        assert "chat" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["chat"]
        assert "messaging" in syns

    def test_all_values_are_lists_of_strings(self):
        for key, syns in KEYWORD_SYNONYMS.items():
            assert isinstance(syns, list), f"{key} value is not a list"
            for s in syns:
                assert isinstance(s, str), f"{key} contains non-string: {s}"
            assert len(syns) >= 2, f"{key} has fewer than 2 synonyms"

    def test_no_empty_strings(self):
        for key, syns in KEYWORD_SYNONYMS.items():
            assert key.strip(), "Empty key found"
            for s in syns:
                assert s.strip(), f"Empty synonym in {key}"
