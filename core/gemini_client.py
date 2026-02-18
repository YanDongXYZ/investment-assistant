"""Gemini API 客户端封装（与 OpenAIClient 接口对齐）"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Optional, List, Dict, Tuple

try:
    from google import genai
except ImportError as e:
    raise ImportError("请先安装 google-genai: pip install google-genai") from e

logger = logging.getLogger(__name__)


class GeminiClient:
    """Gemini API 客户端（默认使用 gemini-3-pro-preview）"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        model_pro: Optional[str] = None,
        model_flash: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 GEMINI_API_KEY 环境变量或在 config.json 中配置 gemini_api_key")

        self.client = genai.Client(api_key=self.api_key)
        resolved_pro = model_pro or model or "gemini-3-pro-preview"
        resolved_flash = model_flash or model or resolved_pro
        self._model_pro = resolved_pro
        self._model_flash = resolved_flash
        self.model = resolved_pro

    def _build_contents(self, prompt: str, history: Optional[List[Dict]] = None) -> List[Dict]:
        contents: List[Dict] = []
        if history:
            for msg in history:
                role = msg.get("role")
                role = "model" if role in ("assistant", "model") else "user"
                contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})
        return contents

    def chat(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        return self.chat_pro(prompt, history)

    def chat_pro(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        contents = self._build_contents(prompt, history)
        resp = self.client.models.generate_content(model=self._model_pro, contents=contents)
        text = getattr(resp, "text", None)
        return text or ""

    def chat_flash(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        contents = self._build_contents(prompt, history)
        resp = self.client.models.generate_content(model=self._model_flash, contents=contents)
        text = getattr(resp, "text", None)
        return text or ""

    def chat_with_system(self, system_prompt: str, user_message: str,
                         history: Optional[List[Dict]] = None) -> str:
        return self.chat_with_system_pro(system_prompt, user_message, history)

    def chat_with_system_pro(self, system_prompt: str, user_message: str,
                             history: Optional[List[Dict]] = None) -> str:
        contents = self._build_contents(user_message, history)
        resp = self.client.models.generate_content(
            model=self._model_pro,
            contents=contents,
            system_instruction=system_prompt,
        )
        text = getattr(resp, "text", None)
        return text or ""

    def chat_with_system_flash(self, system_prompt: str, user_message: str,
                               history: Optional[List[Dict]] = None) -> str:
        contents = self._build_contents(user_message, history)
        resp = self.client.models.generate_content(
            model=self._model_flash,
            contents=contents,
            system_instruction=system_prompt,
        )
        text = getattr(resp, "text", None)
        return text or ""

    def search(self, query: str, time_range_days: int = 7) -> str:
        """降级：不进行联网搜索，仅返回提示。"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)
        return (
            f"[search disabled] 该版本使用 Gemini({self.model})，未接入 Google grounding 搜索。\n"
            f"请手动提供资料或上传文件。\n\n"
            f"query={query}\n"
            f"range={start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}\n"
        )

    def analyze_file(self, file_path: str, prompt: str) -> str:
        """简单文件分析（文本读取 + Pro 模型）"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(8000)
        except Exception as e:
            return f"无法读取文件: {e}"

        full_prompt = f"{prompt}\n\n文件内容（截断）:\n{content}"
        return self.chat_pro(full_prompt)

    @property
    def model_pro(self) -> str:
        return self._model_pro

    def _fetch_google_news_rss(self, query: str, time_range_days: int, limit: int = 8) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """Fetch Google News RSS items.

        Returns (items, error). Each item: {title, link, pubDate, source}.
        """
        try:
            q_str = query
            if "when:" not in q_str:
                q_str = f"{q_str} when:{time_range_days}d"
            q = urllib.parse.quote(q_str)
            url = f"https://news.google.com/rss/search?q={q}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
            with urllib.request.urlopen(url, timeout=20) as resp:
                xml_bytes = resp.read()
            root = ET.fromstring(xml_bytes)
            channel = root.find('channel')
            if channel is None:
                return [], None
            items = []
            for it in channel.findall('item'):
                title = (it.findtext('title') or '').strip()
                link = (it.findtext('link') or '').strip()
                pub_raw = (it.findtext('pubDate') or '').strip()
                try:
                    pub = parsedate_to_datetime(pub_raw).strftime('%Y-%m-%d')
                except Exception:
                    pub = pub_raw
                source = (it.findtext('source') or '').strip()
                if not title:
                    continue
                items.append({"title": title, "link": link, "pubDate": pub, "source": source})
                if len(items) >= limit:
                    break
            return items, None
        except Exception as e:
            return [], str(e)

    def _rss_items_to_structured_news(
        self,
        stock_name: str,
        dimension: str,
        focus: str,
        rss_items: List[Dict[str, str]],
    ) -> List[Dict]:
        if not rss_items:
            return []

        compact = []
        for x in rss_items[:8]:
            compact.append({
                "title": x.get("title", ""),
                "source": x.get("source", ""),
                "date": x.get("pubDate", ""),
                "link": x.get("link", ""),
            })

        prompt = f"""你在做投资环境跟踪。目标公司/标的：{stock_name}

维度：{dimension}
关注点：{focus}

下面是 Google News RSS 抓取到的原始条目（可能有噪音/重复/标题党），请你筛出最多 5 条最重要的，并严格输出 JSON（只输出 JSON，不要解释）：

{{
  \"news\": [
    {{
      \"date\": \"YYYY-MM-DD\",  # 如果无法解析日期，可留空字符串
      \"title\": \"...\",
      \"summary\": \"1-2 句摘要\",
      \"dimension\": \"{dimension}\",
      \"relevance\": \"与投资逻辑的关联说明\",
      \"importance\": \"高/中/低\",
      \"source\": \"...\",
      \"url\": \"...\"
    }}
  ]
}}

原始条目：
{compact}
"""

        text = self.chat_flash(prompt)
        m = re.search(r'\{[\s\S]*\}', text)
        if not m:
            return []
        try:
            obj = json.loads(m.group(0))
            out = obj.get('news', [])
            for n in out:
                n['dimension'] = dimension
            return out[:5]
        except Exception:
            return []

    def search_news_structured(
        self,
        stock_name: str,
        related_entities: List[str],
        time_range_days: int = 7,
        playbook: Optional[Dict] = None,
    ) -> List[Dict]:
        """结构化新闻搜索。"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_range_days)

        dims = [
            ("公司核心动态", f"{stock_name} 财报 业绩 公告 管理层 重大事项", "财报发布、重大公告、人事变动、股东变化"),
            ("行业与竞争", f"{stock_name} 竞争对手 行业格局 市场份额 " + " ".join(related_entities[:3]), "竞争对手动态、行业趋势、市场格局变化"),
            ("产品与技术", f"{stock_name} 新产品 技术突破 研发 创新 专利", "新产品发布、技术进展、研发投入"),
            ("宏观与政策", f"{stock_name} 政策 监管 行业政策 法规", "监管政策变化、行业扶持政策、法规调整"),
        ]

        all_news: List[Dict] = []
        failed = []
        warnings: List[str] = []

        from .retrieval import SearchManager, TavilyProvider, OpenClawWebSearchProvider

        sm = SearchManager(
            providers=[
                TavilyProvider() if os.getenv("TAVILY_API_KEY") else None,
                OpenClawWebSearchProvider(),
            ],
            cache_ttl_seconds=6 * 3600,
            hard_timeout_seconds=20,
        )

        if not sm.providers:
            warnings.append("未配置检索 Provider，降级到 Google News RSS。")
            for dim, q, focus in dims:
                items, err = self._fetch_google_news_rss(q, time_range_days=time_range_days, limit=8)
                if err:
                    failed.append({"dimension": dim, "error": err})
                    continue
                structured = self._rss_items_to_structured_news(stock_name, dim, focus, items)
                all_news.extend(structured)
        else:
            warnings.append("新闻来源=Tavily + Brave Search（union）。")
            for dim, q, focus in dims:
                hits = sm.search(q, max_results=8, topic="news", depth="basic")
                rss_like = [
                    {
                        "title": h.title,
                        "source": h.provider,
                        "pubDate": h.published or "",
                        "link": h.url,
                    }
                    for h in hits
                    if h.title and h.url
                ]
                structured = self._rss_items_to_structured_news(stock_name, dim, focus, rss_like)
                all_news.extend(structured)

        seen = set()
        uniq = []
        for n in all_news:
            t = (n.get('title') or '').lower().strip()[:60]
            if not t or t in seen:
                continue
            seen.add(t)
            uniq.append(n)

        imp = {"高": 0, "中": 1, "低": 2}
        uniq.sort(key=lambda x: (imp.get(x.get('importance', '低'), 2), x.get('date', '')), reverse=False)

        metadata = {
            "_is_metadata": True,
            "total_dimensions": len(dims),
            "successful_dimensions": len(dims) - len(failed),
            "failed_dimensions": failed,
            "search_warnings": [
                *warnings,
                f"range={start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}",
                f"stock={stock_name}",
            ],
        }

        result = uniq[:20]
        result.insert(0, metadata)
        return result

    @property
    def model_flash(self) -> str:
        return self._model_flash
