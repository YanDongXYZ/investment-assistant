"""Tests for core.gemini_client.GeminiClient."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


class TestGeminiClientInit:
    def test_requires_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GEMINI_API_KEY", None)
            from core.gemini_client import GeminiClient
            with pytest.raises(ValueError, match="GEMINI_API_KEY"):
                GeminiClient(api_key=None)

    def test_accepts_explicit_key(self):
        with patch("core.gemini_client.genai.Client"):
            from core.gemini_client import GeminiClient
            c = GeminiClient(api_key="gk-test")
            assert c.api_key == "gk-test"
            assert c.model == "gemini-3-pro-preview"
            assert c.model_pro == "gemini-3-pro-preview"
            assert c.model_flash == "gemini-3-pro-preview"

    def test_model_overrides(self):
        with patch("core.gemini_client.genai.Client"):
            from core.gemini_client import GeminiClient
            c = GeminiClient(api_key="gk-test", model_pro="pro", model_flash="flash")
            assert c.model_pro == "pro"
            assert c.model_flash == "flash"

    def test_env_key_fallback(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gk-env"}):
            with patch("core.gemini_client.genai.Client"):
                from core.gemini_client import GeminiClient
                c = GeminiClient()
                assert c.api_key == "gk-env"


class TestGeminiChat:
    def test_chat_returns_content(self):
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text="mock response")
        with patch("core.gemini_client.genai.Client", return_value=mock_instance):
            from core.gemini_client import GeminiClient
            client = GeminiClient(api_key="gk-test")
            result = client.chat("hello")
            assert result == "mock response"

    def test_chat_with_system_passes_system_instruction(self):
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text="mock response")
        with patch("core.gemini_client.genai.Client", return_value=mock_instance):
            from core.gemini_client import GeminiClient
            client = GeminiClient(api_key="gk-test")
            client.chat_with_system("sys", "usr")
            call_args = mock_instance.models.generate_content.call_args
            assert call_args.kwargs.get("system_instruction") == "sys"

    def test_chat_flash_uses_flash_model(self):
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text="mock response")
        with patch("core.gemini_client.genai.Client", return_value=mock_instance):
            from core.gemini_client import GeminiClient
            client = GeminiClient(api_key="gk-test", model_pro="pro", model_flash="flash")
            client.chat_flash("hello")
            call_args = mock_instance.models.generate_content.call_args
            assert call_args.kwargs.get("model") == "flash"

    def test_chat_history_role_mapping(self):
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = MagicMock(text="mock response")
        with patch("core.gemini_client.genai.Client", return_value=mock_instance):
            from core.gemini_client import GeminiClient
            client = GeminiClient(api_key="gk-test")
            client.chat("q", history=[
                {"role": "user", "content": "prev"},
                {"role": "model", "content": "ans"},
            ])
            call_args = mock_instance.models.generate_content.call_args
            contents = call_args.kwargs.get("contents")
            roles = [c.get("role") for c in contents]
            assert "model" in roles
