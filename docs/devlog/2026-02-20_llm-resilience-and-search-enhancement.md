# 2026-02-20: LLM 调用韧性加固 + 搜索增强

## 背景

深度研究流程中，Gemini API 频繁返回 503 (UNAVAILABLE: high demand)，导致 Web 端多个接口直接崩溃返回 500。同时，搜索链路缺乏调试日志，排障困难。

## 变更概要

### 1. LLM 调用全面异常保护

**问题**: `chat_pro()` / `chat_flash()` 调用散布在 6 个模块中，均无 try/except，任何 API 异常（503、SSL、超时）都会导致请求崩溃。

**修复**: 对所有 12 处 LLM 调用点加上异常保护，策略分两层：

| 层级 | 策略 | 适用场景 |
|------|------|---------|
| core 层 | 重试 + 退避 + 降级返回 | `assess_impact`, `execute_research` |
| core 层 | try/except + 降级返回 | `search_news_structured (RSS)`, `interview`, `preference_learner`, `collect_news` |
| web 路由层 | try/except + JSON 错误响应 | 所有 `/api/research/*` 端点 |

**涉及文件**:
- `core/environment.py` — `assess_impact` 重试3次 + `collect_news` / `search_news_structured` 异常捕获
- `core/research.py` — `execute_research` 重试3次
- `core/interview.py` — `continue_portfolio_interview` / `continue_stock_interview` 异常降级
- `core/preference_learner.py` — `extract_preferences_from_interactions` 异常降级
- `core/gemini_client.py` — `_rss_items_to_structured_news` 的 `chat_flash` 异常降级
- `core/openai_client.py` — 同上
- `web/app.py` — 6 个路由端点加 try/except（assess, execute x2, adjust-plan, ask-question, collect_news x2）

### 2. 搜索链路增强（英文别名 + RSS fallback）

**问题**: 中文股票名搜索命中率低，Tavily/OpenClaw 均不可用时无 fallback。

**修复**:
- `search_news_structured()` 新增英文别名并行搜索（从 ticker + related_entities 提取）
- 新增 RSS fallback 触发条件：无 provider 或去重后结果 < 10 条
- 搜索结果去重（`_dedup_by_title`）
- 同步应用到 `gemini_client.py` 和 `openai_client.py`

### 3. 全链路调试日志

**问题**: 搜索结果为 0 时无法定位是哪个环节失败。

**修复**: 在 `retrieval.py`、`environment.py`、`openai_client.py`、`gemini_client.py`、`research.py` 中添加结构化日志，覆盖 Provider 初始化、搜索请求/响应、缓存命中、维度成功/失败等关键节点。

### 4. Bug 修复

- `environment.py`: `logger` 原为 `collect_news()` 内局部变量，`assess_impact()` 无法访问 → 提升到模块级别
- `environment.py`: `len(None)` 错误 → 将日志行移到 None 类型检查之后
- `retrieval.py`: Provider 初始化异常导致整个 SearchManager 不可用 → 加 safe init

## 测试

50 项测试全部通过，无回归。

```
============================== 50 passed in 0.65s ==============================
```

## 修改文件清单

```
core/environment.py          # assess_impact 重试, collect_news 异常保护, 模块级 logger
core/research.py             # execute_research 重试, 添加 logger
core/interview.py            # 两处 chat_flash 异常保护, 添加 logger
core/preference_learner.py   # chat_pro 异常保护, 添加 logger
core/gemini_client.py        # RSS chat_flash 降级, 英文别名搜索, safe provider init
core/openai_client.py        # 同 gemini_client.py
core/retrieval.py            # 全链路调试日志, safe provider init
core/storage.py              # 小调整
core/llm_factory.py          # 小调整
web/app.py                   # 6 个路由端点异常保护
web/templates/settings.html  # 小调整
```
