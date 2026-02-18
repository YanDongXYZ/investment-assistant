"""Tests for core.llm_factory."""

from __future__ import annotations

from unittest.mock import patch

from core.llm_factory import (
    resolve_llm_provider,
    resolve_llm_model_pro,
    resolve_llm_model_flash,
    resolve_llm_model,
    create_llm_client,
    GEMINI_DEFAULT_MODEL_PRO,
    GEMINI_DEFAULT_MODEL_FLASH,
    OPENAI_DEFAULT_MODEL_PRO,
    OPENAI_DEFAULT_MODEL_FLASH,
)


def test_resolve_provider_prefers_config(tmp_storage):
    tmp_storage.set_llm_provider("gemini")
    tmp_storage.set_gemini_api_key("gk-test")
    assert resolve_llm_provider(tmp_storage) == "gemini"


def test_resolve_provider_fallback_to_openai(tmp_storage):
    tmp_storage.set_openai_api_key("sk-test")
    assert resolve_llm_provider(tmp_storage) == "openai"


def test_resolve_model_defaults(tmp_storage):
    tmp_storage.set_llm_provider("gemini")
    assert resolve_llm_model(tmp_storage, "gemini") == GEMINI_DEFAULT_MODEL_PRO
    assert resolve_llm_model_pro(tmp_storage, "gemini") == GEMINI_DEFAULT_MODEL_PRO
    assert resolve_llm_model_flash(tmp_storage, "gemini") == GEMINI_DEFAULT_MODEL_FLASH
    assert resolve_llm_model_pro(tmp_storage, "openai") == OPENAI_DEFAULT_MODEL_PRO
    assert resolve_llm_model_flash(tmp_storage, "openai") == OPENAI_DEFAULT_MODEL_FLASH


def test_create_gemini_client(tmp_storage):
    tmp_storage.set_llm_provider("gemini")
    tmp_storage.set_gemini_api_key("gk-test")
    with patch("core.llm_factory.GeminiClient") as MockClient:
        create_llm_client(tmp_storage)
        MockClient.assert_called_once()


def test_create_openai_client(tmp_storage):
    tmp_storage.set_llm_provider("openai")
    tmp_storage.set_openai_api_key("sk-test")
    with patch("core.llm_factory.OpenAIClient") as MockClient:
        create_llm_client(tmp_storage)
        MockClient.assert_called_once()
