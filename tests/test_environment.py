"""Tests for core.environment.EnvironmentCollector — collect_news return type."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestCollectNewsReturnType:
    """collect_news must return Dict{'news': list, 'search_metadata': dict}."""

    def test_returns_dict_with_news_key(self, mock_openai_client, tmp_storage):
        from core.environment import EnvironmentCollector
        ec = EnvironmentCollector(mock_openai_client, tmp_storage)

        # Mock search_news_structured to return a typical List[Dict]
        mock_openai_client.search_news_structured = MagicMock(return_value=[
            {"_is_metadata": True, "total_dimensions": 4, "successful_dimensions": 4,
             "failed_dimensions": [], "search_warnings": []},
            {"title": "News1", "date": "2026-01-01", "importance": "high"},
        ])

        result = ec.collect_news("test_corp", "TestCorp", 7)
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "news" in result
        assert "search_metadata" in result
        assert isinstance(result["news"], list)
        assert isinstance(result["search_metadata"], dict)

    def test_handles_string_fallback(self, mock_openai_client, tmp_storage):
        from core.environment import EnvironmentCollector
        ec = EnvironmentCollector(mock_openai_client, tmp_storage)
        mock_openai_client.search_news_structured = MagicMock(return_value="search disabled")

        result = ec.collect_news("x", "X", 7)
        assert isinstance(result, dict)
        assert result["news"] == []
        warnings = result["search_metadata"].get("search_warnings", [])
        assert any("降级" in w for w in warnings)

    def test_handles_none_fallback(self, mock_openai_client, tmp_storage):
        from core.environment import EnvironmentCollector
        ec = EnvironmentCollector(mock_openai_client, tmp_storage)
        mock_openai_client.search_news_structured = MagicMock(return_value=None)

        result = ec.collect_news("x", "X", 7)
        assert isinstance(result, dict)
        assert result["news"] == []
