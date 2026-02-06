"""Unit tests for OpenAIClient."""

import pytest
from unittest.mock import MagicMock, patch

from core.openai_client import OpenAIClient


class TestOpenAIClientInit:
    def test_init_with_explicit_key(self, mock_openai_client):
        client = OpenAIClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.model == "gpt-5.2"

    def test_init_with_env_key(self, mock_openai_client):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}):
            client = OpenAIClient()
            assert client.api_key == "env-key"

    def test_init_missing_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            # Ensure OPENAI_API_KEY is not set
            import os
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIClient(api_key=None)

    def test_custom_model(self, mock_openai_client):
        client = OpenAIClient(api_key="k", model="gpt-4o")
        assert client.model == "gpt-4o"


class TestOpenAIClientChat:
    def test_chat_simple(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        result = client.chat("hello")
        assert result == "mock response"
        call_args = mock_openai_client["client_instance"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "hello"
        assert call_args.kwargs["timeout"] == 120

    def test_chat_with_history(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        history = [
            {"role": "user", "content": "q1"},
            {"role": "model", "content": "a1"},  # Gemini-style "model" role
        ]
        client.chat("q2", history=history)
        call_args = mock_openai_client["client_instance"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"  # "model" mapped to "assistant"
        assert messages[2]["content"] == "q2"

    def test_chat_with_system(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        result = client.chat_with_system("you are helpful", "do something")
        call_args = mock_openai_client["client_instance"].chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "you are helpful"
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "do something"


class TestOpenAIClientSearch:
    def test_search_returns_disabled_message(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        result = client.search("test query")
        assert "[search disabled]" in result
        assert "test query" in result


class TestOpenAIClientProperties:
    def test_model_pro(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        assert client.model_pro == client.model

    def test_model_flash(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        assert client.model_flash == client.model


class TestOpenAIClientRSS:
    def test_fetch_google_news_rss_error(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        with patch("core.openai_client.urllib.request.urlopen", side_effect=Exception("network error")):
            items, err = client._fetch_google_news_rss("test", 7)
            assert items == []
            assert "network error" in err

    def test_rss_items_to_structured_news_empty(self, mock_openai_client):
        client = OpenAIClient(api_key="k")
        result = client._rss_items_to_structured_news("Stock", "dim", "focus", [])
        assert result == []

    def test_rss_items_to_structured_news_parses_json(self, mock_openai_client):
        mock_openai_client["response"].choices[0].message.content = '{"news": [{"title": "t1", "date": "2025-01-01", "summary": "s", "dimension": "x", "relevance": "r", "importance": "\u9ad8", "source": "src", "url": "http://x"}]}'
        client = OpenAIClient(api_key="k")
        items = [{"title": "Raw Title", "source": "S", "pubDate": "2025-01-01", "link": "http://x"}]
        result = client._rss_items_to_structured_news("Stock", "dim", "focus", items)
        assert len(result) == 1
        assert result[0]["dimension"] == "dim"
