"""LLM client factory and configuration helpers."""

from __future__ import annotations

import os
from typing import Optional, Dict

from .storage import Storage
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient

OPENAI_DEFAULT_MODEL_PRO = "gpt-5.2"
OPENAI_DEFAULT_MODEL_FLASH = "gpt-5.2"
GEMINI_DEFAULT_MODEL_PRO = "gemini-3-pro-preview"
GEMINI_DEFAULT_MODEL_FLASH = "gemini-3-flash-preview"
GEMINI_MODELS = ["gemini-3-pro-preview", "gemini-3-flash-preview"]
SUPPORTED_PROVIDERS = ("openai", "gemini")


def normalize_provider(provider: Optional[str]) -> Optional[str]:
    if not provider:
        return None
    provider = provider.strip().lower()
    return provider if provider in SUPPORTED_PROVIDERS else None


def resolve_llm_provider(storage: Storage, override: Optional[str] = None) -> str:
    provider = (
        normalize_provider(override)
        or normalize_provider(os.getenv("IA_PROVIDER"))
        or normalize_provider(storage.get_llm_provider())
    )
    if provider:
        return provider
    if storage.get_openai_api_key():
        return "openai"
    if storage.get_gemini_api_key():
        return "gemini"
    return "openai"


def resolve_llm_model_pro(storage: Storage, provider: str, override: Optional[str] = None) -> str:
    model = (
        override
        or os.getenv("IA_MODEL_PRO")
        or storage.get_llm_model_pro()
        or storage.get_llm_model()
    )
    if model:
        return model
    if provider == "gemini":
        return GEMINI_DEFAULT_MODEL_PRO
    return OPENAI_DEFAULT_MODEL_PRO


def resolve_llm_model_flash(storage: Storage, provider: str, override: Optional[str] = None) -> str:
    model = (
        override
        or os.getenv("IA_MODEL_FLASH")
        or storage.get_llm_model_flash()
        or storage.get_llm_model()
    )
    if model:
        return model
    if provider == "gemini":
        return GEMINI_DEFAULT_MODEL_FLASH
    return OPENAI_DEFAULT_MODEL_FLASH


def resolve_llm_model(storage: Storage, provider: str, override: Optional[str] = None) -> str:
    return resolve_llm_model_pro(storage, provider, override)


def get_llm_config(storage: Storage) -> Dict[str, str]:
    provider = resolve_llm_provider(storage)
    model_pro = resolve_llm_model_pro(storage, provider)
    model_flash = resolve_llm_model_flash(storage, provider)
    return {"provider": provider, "model": model_pro, "model_pro": model_pro, "model_flash": model_flash}


def create_llm_client(
    storage: Storage,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    model_pro: Optional[str] = None,
    model_flash: Optional[str] = None,
):
    provider = resolve_llm_provider(storage, provider)
    if model and not model_pro:
        model_pro = model
    if model and not model_flash:
        model_flash = model
    model_pro = resolve_llm_model_pro(storage, provider, model_pro)
    model_flash = resolve_llm_model_flash(storage, provider, model_flash)

    if provider == "gemini":
        api_key = storage.get_gemini_api_key()
        if not api_key:
            raise ValueError("请设置 GEMINI_API_KEY 环境变量或在 config.json 中配置 gemini_api_key")
        return GeminiClient(api_key=api_key, model_pro=model_pro, model_flash=model_flash)

    api_key = storage.get_openai_api_key()
    if not api_key:
        raise ValueError("请设置 OPENAI_API_KEY 环境变量或在 config.json 中配置 openai_api_key")
    return OpenAIClient(api_key=api_key, model_pro=model_pro, model_flash=model_flash)
