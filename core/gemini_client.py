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
        tavily_api_key: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("请设置 GEMINI_API_KEY 环境变量或在 config.json 中配置 gemini_api_key")

        self._tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
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

        try:
            text = self.chat_flash(prompt)
        except Exception as e:
            logger.error(f"[_rss_items_to_structured_news] chat_flash failed for {dimension}: {type(e).__name__}: {e}")
            # LLM 不可用时直接返回原始条目（降级）
            fallback = []
            for x in compact[:5]:
                fallback.append({
                    "date": x.get("date", ""),
                    "title": x.get("title", ""),
                    "summary": x.get("title", ""),
                    "dimension": dimension,
                    "relevance": "（LLM 不可用，未做筛选）",
                    "importance": "中",
                    "source": x.get("source", ""),
                    "url": x.get("link", ""),
                })
            return fallback

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

    def _is_english_like(self, text: str) -> bool:
        if not text:
            return False
        return bool(re.search(r"[A-Za-z]", text))

    def _collect_english_aliases(
        self,
        stock_name: str,
        related_entities: List[str],
        playbook: Optional[Dict] = None,
    ) -> List[str]:
        aliases: List[str] = []
        if self._is_english_like(stock_name):
            aliases.append(stock_name)
        ticker = (playbook or {}).get("ticker", "") if playbook else ""
        if ticker and ticker not in aliases:
            aliases.append(ticker)
        for ent in related_entities or []:
            if self._is_english_like(ent) and ent not in aliases:
                aliases.append(ent)
        return aliases[:3]

    def _build_english_query(self, dimension: str, aliases: List[str]) -> str:
        if not aliases:
            return ""
        alias_str = " ".join(aliases).strip()
        if not alias_str:
            return ""
        keywords = {
            "公司核心动态": "earnings financial results announcement management",
            "行业与竞争": "competitors industry market share",
            "产品与技术": "product technology innovation R&D patent",
            "宏观与政策": "policy regulation macro",
        }
        return f"{alias_str} {keywords.get(dimension, 'news')}".strip()

    def search_news_structured(
        self,
        stock_name: str,
        related_entities: List[str],
        time_range_days: int = 7,
        playbook: Optional[Dict] = None,
    ) -> List[Dict]:
        """结构化新闻搜索。"""
        logger.info(f"[search_news_structured] Starting for {stock_name}, range={time_range_days}d")

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

        english_aliases = self._collect_english_aliases(stock_name, related_entities, playbook)
        if english_aliases:
            logger.debug(f"[search_news_structured] English aliases: {english_aliases}")

        rss_fallback_triggered = False
        rss_fallback_reason: List[str] = []
        total_rss_items = 0
        missing_dims: List[tuple] = []

        from .retrieval import SearchManager, TavilyProvider, OpenClawWebSearchProvider

        tavily_key = self._tavily_api_key
        providers = []
        if tavily_key:
            try:
                providers.append(TavilyProvider(api_key=tavily_key))
            except Exception as e:
                logger.error(f"[search_news_structured] TavilyProvider init failed: {e}")
        try:
            oc = OpenClawWebSearchProvider()
            if oc.is_available():
                providers.append(oc)
        except Exception as e:
            logger.error(f"[search_news_structured] OpenClawWebSearchProvider init failed: {e}")

        sm = SearchManager(
            providers=providers,
            cache_ttl_seconds=6 * 3600,
            hard_timeout_seconds=20,
        )
        logger.info(f"[search_news_structured] {len(sm.providers)} provider(s)")

        def _merge_hits(a, b):
            merged, seen = [], set()
            for h in (a or []) + (b or []):
                url = (h.url or "").strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                merged.append(h)
            return merged

        def _dedup_by_title(items: List[Dict]) -> List[Dict]:
            seen_t, out = set(), []
            for n in items:
                t = (n.get('title') or '').lower().strip()[:60]
                if not t or t in seen_t:
                    continue
                seen_t.add(t)
                out.append(n)
            return out

        if not sm.providers:
            warnings.append("未配置检索 Provider，降级到 Google News RSS。")
            rss_fallback_triggered = True
            rss_fallback_reason.append("no_providers")
            for dim, q, focus in dims:
                items, err = self._fetch_google_news_rss(q, time_range_days=time_range_days, limit=8)
                if err:
                    failed.append({"dimension": dim, "error": err})
                    continue
                total_rss_items += len(items)
                structured = self._rss_items_to_structured_news(stock_name, dim, focus, items)
                all_news.extend(structured)
        else:
            warnings.append("新闻来源=Tavily + Brave Search（union）。")
            for dim, q, focus in dims:
                cn_hits = sm.search(q, max_results=8, topic="news", depth="basic")
                en_hits = []
                en_query = self._build_english_query(dim, english_aliases)
                if en_query:
                    en_hits = sm.search(en_query, max_results=8, topic="news", depth="basic")

                hits = _merge_hits(cn_hits, en_hits)
                if not hits:
                    missing_dims.append((dim, q, focus))

                rss_like = [
                    {"title": h.title, "source": h.provider, "pubDate": h.published or "", "link": h.url}
                    for h in hits if h.title and h.url
                ]
                structured = self._rss_items_to_structured_news(stock_name, dim, focus, rss_like)
                all_news.extend(structured)

            uniq_pre = _dedup_by_title(all_news)
            if len(uniq_pre) < 10 or missing_dims:
                rss_fallback_triggered = True
                if len(uniq_pre) < 10:
                    rss_fallback_reason.append("low_results")
                if missing_dims:
                    rss_fallback_reason.append("missing_dimensions")
                dims_to_fetch = dims if len(uniq_pre) < 10 else missing_dims
                logger.info(f"[search_news_structured] RSS fallback: uniq={len(uniq_pre)}, missing={len(missing_dims)}")
                for dim, q, focus in dims_to_fetch:
                    items, err = self._fetch_google_news_rss(q, time_range_days=time_range_days, limit=8)
                    if err:
                        failed.append({"dimension": dim, "error": err})
                        continue
                    total_rss_items += len(items)
                    structured = self._rss_items_to_structured_news(stock_name, dim, focus, items)
                    all_news.extend(structured)

        uniq = _dedup_by_title(all_news)

        imp = {"高": 0, "中": 1, "低": 2}
        uniq.sort(key=lambda x: (imp.get(x.get('importance', '低'), 2), x.get('date', '')), reverse=False)

        metadata = {
            "_is_metadata": True,
            "total_dimensions": len(dims),
            "successful_dimensions": len(dims) - len(failed),
            "failed_dimensions": failed,
            "rss_fallback_triggered": rss_fallback_triggered,
            "rss_fallback_reason": rss_fallback_reason,
            "total_rss_items": total_rss_items,
            "search_warnings": [
                *warnings,
                f"range={start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}",
                f"stock={stock_name}",
            ],
        }

        logger.info(f"[search_news_structured] Final: {len(uniq)} items, fallback={rss_fallback_triggered}")
        result = uniq[:20]
        result.insert(0, metadata)
        return result

    @property
    def model_flash(self) -> str:
        return self._model_flash
