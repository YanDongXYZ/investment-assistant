"""Tests for core.retrieval (SearchManager, caching, union merge)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.retrieval import SearchManager, SearchProvider, SearchResult, format_search_results_for_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _StubProvider(SearchProvider):
    def __init__(self, results=None, available=True, name="stub"):
        self.name = name
        self._results = results or []
        self._available = available

    def is_available(self):
        return self._available

    def search(self, query, *, max_results=5, topic="news", depth="basic"):
        return self._results


class _FailingProvider(SearchProvider):
    name = "failing"

    def search(self, query, **kw):
        raise RuntimeError("provider error")


# ---------------------------------------------------------------------------
# SearchManager
# ---------------------------------------------------------------------------

class TestSearchManager:
    def test_union_merge(self, tmp_path):
        r1 = SearchResult("A", "https://a.com", "a", "p1")
        r2 = SearchResult("B", "https://b.com", "b", "p2")
        r3 = SearchResult("A dup", "https://a.com", "a", "p2")  # dup URL

        with patch("core.retrieval.SEARCH_CACHE_DIR", tmp_path):
            sm = SearchManager(
                providers=[_StubProvider([r1], name="s1"), _StubProvider([r2, r3], name="s2")],
                cache_ttl_seconds=3600,
            )
            results = sm.search("q")
            urls = [r.url for r in results]
            assert urls == ["https://a.com", "https://b.com"]  # no dup

    def test_cache_hit(self, tmp_path):
        r = SearchResult("C", "https://c.com", "c", "stub")
        provider = _StubProvider([r])

        with patch("core.retrieval.SEARCH_CACHE_DIR", tmp_path):
            sm = SearchManager(providers=[provider], cache_ttl_seconds=3600)
            first = sm.search("cached")
            assert len(first) == 1

            # Replace provider with empty one; cache should still return
            sm.providers = [_StubProvider([])]
            second = sm.search("cached")
            assert len(second) == 1
            assert second[0].title == "C"

    def test_provider_failure_skips(self, tmp_path):
        r = SearchResult("D", "https://d.com", "d", "stub")
        with patch("core.retrieval.SEARCH_CACHE_DIR", tmp_path):
            sm = SearchManager(
                providers=[_FailingProvider(), _StubProvider([r])],
                cache_ttl_seconds=3600,
            )
            results = sm.search("q")
            assert len(results) == 1
            assert results[0].title == "D"

    def test_unavailable_provider_skipped(self, tmp_path):
        with patch("core.retrieval.SEARCH_CACHE_DIR", tmp_path):
            sm = SearchManager(
                providers=[_StubProvider([], available=False)],
            )
            results = sm.search("q")
            assert results == []

    def test_max_results_cap(self, tmp_path):
        items = [SearchResult(f"R{i}", f"https://r{i}.com", "", "s") for i in range(10)]
        with patch("core.retrieval.SEARCH_CACHE_DIR", tmp_path):
            sm = SearchManager(providers=[_StubProvider(items)])
            results = sm.search("q", max_results=3)
            assert len(results) == 3


# ---------------------------------------------------------------------------
# format_search_results_for_prompt
# ---------------------------------------------------------------------------

class TestFormatResults:
    def test_empty(self):
        assert format_search_results_for_prompt([]) == "(no search results)"

    def test_limit(self):
        items = [SearchResult(f"T{i}", f"https://u{i}.com", f"s{i}", "p") for i in range(10)]
        text = format_search_results_for_prompt(items, limit=3)
        assert "[3]" in text
        assert "[4]" not in text
