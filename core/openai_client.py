"""OpenAI API 客户端封装（替代 Gemini）

目标：尽量保持与原 GeminiClient 一致的接口（chat/chat_with_system/search），
以便项目在不大改业务逻辑的情况下切换到 GPT-5.2。

注意：原项目的 Gemini search grounding / 结构化新闻搜索依赖 Google Search 工具。
这里默认提供降级实现（返回提示/空结果），保证系统可跑通；如需联网搜索，
后续可接入独立搜索服务。
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

try:
    from openai import OpenAI
except ImportError as e:
    raise ImportError("请先安装 openai: pip install openai") from e


class OpenAIClient:
    """OpenAI API 客户端（默认使用 gpt-5.2）"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-5.2"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 OPENAI_API_KEY 环境变量或在 config.json 中配置 openai_api_key")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def chat(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        """普通对话（与 GeminiClient.chat 对齐）"""
        messages: List[Dict[str, str]] = []
        if history:
            for msg in history:
                role = msg.get("role")
                if role in ("assistant", "model"):
                    role = "assistant"
                else:
                    role = "user"
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": prompt})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return resp.choices[0].message.content or ""

    def chat_with_system(self, system_prompt: str, user_message: str,
                         history: Optional[List[Dict]] = None) -> str:
        """带系统提示的对话（与 GeminiClient.chat_with_system 对齐）"""
        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]

        if history:
            for msg in history:
                role = msg.get("role")
                if role in ("assistant", "model"):
                    role = "assistant"
                else:
                    role = "user"
                messages.append({"role": role, "content": msg.get("content", "")})

        messages.append({"role": "user", "content": user_message})

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return resp.choices[0].message.content or ""

    def search(self, query: str, time_range_days: int = 7) -> str:
        """降级：不进行联网搜索，仅返回提示。

        原 GeminiClient.search 使用 Google Search grounding。
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)
        return (
            f"[search disabled] 该版本使用 OpenAI({self.model})，未接入 Google grounding 搜索。\n"
            f"请手动提供资料或上传文件。\n\n"
            f"query={query}\n"
            f"range={start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}\n"
        )

    # 兼容调用方可能使用的属性名
    @property
    def model_pro(self) -> str:
        return self.model

    def search_news_structured(
        self,
        stock_name: str,
        related_entities: List[str],
        time_range_days: int = 7,
        playbook: Optional[Dict] = None,
    ) -> List[Dict]:
        """降级版结构化新闻搜索：返回空新闻 + 元数据警告，避免流程报错。

        原 GeminiClient.search_news_structured 依赖 Google Search grounding。
        当前 OpenAIClient 未接入联网搜索，因此只能返回空结果。
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)
        metadata = {
            "_is_metadata": True,
            "total_dimensions": 0,
            "successful_dimensions": 0,
            "failed_dimensions": [],
            "search_warnings": [
                "OpenAIClient 未接入联网搜索，已返回空新闻列表。可在 CLI 选择上传资料以辅助判断。",
                f"range={start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}",
                f"stock={stock_name}",
            ],
        }
        return [metadata]

    @property
    def model_flash(self) -> str:
        return self.model
