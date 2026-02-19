# 投资研究助手 - CODEBUDDY.md

## 项目概述

投资研究助手（Investment Research Assistant）是一个基于 AI 的个人投资研究系统，帮助投资者：
- 系统化管理投资逻辑（Playbook 系统）
- 追踪市场变化与信息关联（环境采集）
- 生成深度研究报告（Deep Research 引擎）
- 学习和优化投资决策（偏好学习系统）

**当前技术栈：** Python 3.11 | Flask 3.0+ | OpenAI GPT-5.2 / Gemini 3 Pro（双模型可切换）| Tavily + OpenClaw 联合检索 + Google News RSS fallback

---

## 核心模块与职责

### 1. **LLM 工厂** (`core/llm_factory.py`)
- **职责**：动态选择 LLM 提供商（OpenAI / Gemini），解析模型配置
- **核心函数**：
  - `create_llm_client(storage)` → 返回 `OpenAIClient` 或 `GeminiClient`
  - `resolve_llm_provider(storage)` → 优先级：override > env(`IA_PROVIDER`) > config > 自动检测
  - `get_llm_config(storage)` → 返回 `{provider, model, model_pro, model_flash}`
- **配置优先级**：环境变量 > `~/.investment-assistant/config.json` > 硬编码默认值

### 2. **LLM 客户端** (`core/openai_client.py` + `core/gemini_client.py`)
- **职责**：LLM API 通信，两个客户端接口完全对齐，可互相切换
- **统一接口**：
  - `chat()` / `chat_pro()` / `chat_flash()` — 三档模型调用
  - `chat_with_system()` / `chat_with_system_pro()` / `chat_with_system_flash()` — 带系统提示
  - `search_news_structured()` — 四维度结构化新闻搜索（公司核心动态、行业与竞争、产品与技术、宏观与政策）
  - `analyze_file()` — 文件分析
- **搜索增强**：
  - 英文别名并行搜索（从 `ticker` + `related_entities` 提取）
  - RSS fallback（无 Provider 或结果 < 10 条时降级到 Google News RSS）
  - 结果去重（`_dedup_by_title`）
- **异常保护**：`_rss_items_to_structured_news()` 中 `chat_flash` 失败时降级返回原始 RSS 条目

### 3. **检索层** (`core/retrieval.py`)
- **职责**：统一搜索管理，多源检索 + 缓存 + 降级
- **核心类**：
  - `SearchManager` — 统一入口，合并多 Provider 结果（URL 去重）
  - `TavilyProvider` — Tavily API（优先），safe init
  - `OpenClawWebSearchProvider` — Brave Search（via OpenClaw Gateway），safe init
  - `SearchResult` — 标准化结果数据类
- **缓存**：文件缓存，TTL 12 小时，路径 `~/.investment-assistant/cache/search/`
- **日志**：全链路调试日志（Provider 初始化、查询、缓存命中、错误详情）
- **关键约定**：禁止直接调用 Brave HTTP API，必须通过 OpenClaw Gateway

### 4. **环境采集** (`core/environment.py`)
- **职责**：多维度新闻搜索与三维度影响评估
- **核心方法**：
  - `collect_news(stock_id, stock_name, time_range_days)` → `{"news": List, "search_metadata": Dict}`
  - `assess_impact(stock_id, time_range, auto_collected, user_uploaded)` → 评估结果 JSON
  - `analyze_file(file_path)` → 文件分析结果
- **异常保护**：
  - `collect_news`：`search_news_structured` 调用 try/except，降级为空列表
  - `assess_impact`：`chat_pro` 最多重试 2 次（退避 2^n 秒），全部失败返回降级结果
- **assess_impact 数据源**：portfolio_playbook、stock_playbook、recent_research、research_context（含反馈）、user_preferences、historical_uploads

### 5. **Deep Research 引擎** (`core/research.py`)
- **职责**：基于研究计划执行搜索，生成深度研究报告
- **核心方法**：
  - `execute_research(stock_id, research_plan, environment_data)` → 完整报告 + 结论 JSON
  - `save_research_record(...)` — 保存研究记录
- **流程**：获取上下文 → `_execute_searches()` 执行搜索计划 → `chat_pro()` 生成报告 → `_extract_conclusion()` 解析
- **异常保护**：`chat_pro` 最多重试 2 次（退避 2^n 秒），全部失败返回降级结果

### 6. **苏格拉底访谈** (`core/interview.py`)
- **职责**：对话式指导用户建立/更新 Playbook
- **核心方法**：
  - `start_portfolio_interview()` / `continue_portfolio_interview(user_input)` — 总体 Playbook
  - `start_stock_interview(stock_name)` / `continue_stock_interview(user_input, stock_name)` — 个股 Playbook
  - `start_update_portfolio_interview(current)` / `start_update_stock_interview(stock_name, current)` — 更新访谈
- **返回格式**：`(AI 响应文本, Playbook Dict | None)`
- **异常保护**：`chat_flash` 失败时返回错误提示，不中断对话历史

### 7. **偏好学习系统** (`core/preference_learner.py`)
- **职责**：记录用户决策行为，AI 提取偏好模式，优化后续建议
- **记录方法**：`log_feedback_interaction()`、`log_plan_adjustment()`、`log_follow_up_question()`、`log_playbook_edit()`
- **学习方法**：`extract_preferences_from_interactions(limit)` → AI 分析交互历史
- **应用方法**：`get_preferences_context()` → 返回供 prompt 注入的偏好文本
- **异常保护**：`chat_pro` 失败时返回空偏好

### 8. **本地存储** (`core/storage.py`)
- **职责**：所有用户数据的 JSON 文件持久化
- **数据位置**：
  ```
  ~/.investment-assistant/
  ├── config.json                # 全局配置（API Key、LLM 设置）
  ├── portfolio_playbook.json    # 总体投资框架
  ├── user_preferences.json      # 用户偏好规则
  ├── interactions.jsonl          # 交互日志（JSONL 格式）
  ├── stocks/{stock_id}/
  │   ├── playbook.json          # 个股投资逻辑
  │   ├── history.json           # 研究历史
  │   └── uploads/               # 用户上传的研报、文件
  ├── cache/
  │   └── search/                # 搜索结果缓存（SHA256 哈希键）
  └── logs/                      # 日志文件（按日期）
  ```
- **配置管理**：支持 `openai_api_key`、`gemini_api_key`、`tavily_api_key`、`llm_provider`、`llm_model_pro`、`llm_model_flash`

### 9. **Tavily 检索** (`core/tavily_search.py`)
- **职责**：Tavily API 薄包装，标准化搜索结果
- **依赖**：`TAVILY_API_KEY` 环境变量（可选；无则降级 RSS）

### 10. **CLI 入口** (`assistant.py`)
- **职责**：多行交互式命令行界面，支持 JSON 编辑和命令路由
- **主要功能**：Playbook 管理、苏格拉底访谈、研究执行与历史查看、配置管理

### 11. **Web UI** (`web/app.py`)
- **职责**：Flask Web 界面，完整 API + 页面路由
- **页面路由**：
  - `/` — 首页仪表盘
  - `/stock/<stock_id>` — 个股详情（研究全流程）
  - `/portfolio` — 总体 Playbook 编辑
  - `/settings` — 系统设置（LLM 配置、API Key）
  - `/stocks` — 股票列表
  - `/add-stock` — 添加股票
  - `/batch-scan` — 批量扫描持仓
  - `/preferences` — 用户偏好管理
  - `/research-history` — 研究历史
- **API 路由**：
  - `POST /api/config/llm` / `POST /api/config/keys` — 配置管理
  - `GET/POST /api/portfolio` — 总体 Playbook CRUD
  - `GET/POST/DELETE /api/stock/<stock_id>` — 个股 Playbook CRUD
  - `POST /api/interview/start` / `POST /api/interview/continue` — 访谈
  - `POST /api/research/<stock_id>/environment` — 采集环境
  - `POST /api/research/<stock_id>/assess` — 三维度评估
  - `POST /api/research/<stock_id>/adjust-plan` — 调整研究计划
  - `POST /api/research/<stock_id>/execute` — 执行深度研究
  - `POST /api/research/<stock_id>/follow-up` — 追问
  - `POST /api/research/<stock_id>/feedback` — 收集反馈
  - `GET /api/research/<stock_id>/history` / `GET /api/research/<stock_id>/context` — 历史与上下文
  - `GET /api/preferences` — 偏好查询
  - `POST /api/batch-scan/scan/<stock_id>` — 批量扫描单股
  - `POST /api/batch-scan/research/<stock_id>` — 批量扫描研究
- **异常保护**：所有涉及 LLM 调用的路由均有 try/except，返回结构化 JSON 错误

### 12. **显示层** (`utils/display.py`)
- **职责**：终端格式化输出（使用 `rich` 库）

---

## 关键约定 & 设计模式

### LLM 调用异常保护规范

所有 `chat_pro()` / `chat_flash()` / `chat()` 调用**必须**有异常保护：

| 场景 | 策略 | 示例 |
|------|------|------|
| 核心研究流程 | 重试 2 次 + 退避等待 + 降级返回 | `assess_impact`, `execute_research` |
| 辅助处理 | try/except + 降级返回 | `interview`, `preference_learner`, RSS 结构化 |
| Web 路由层 | try/except + JSON 错误响应 (500) | 所有 `/api/research/*` 端点 |

```python
# 重试模式（核心流程）
max_retries = 2
response = None
last_error = None
for attempt in range(max_retries + 1):
    try:
        response = self.client.chat_pro(prompt)
        break
    except Exception as e:
        last_error = e
        logger.warning(f"attempt {attempt+1} failed: {e}")
        if attempt < max_retries:
            import time
            time.sleep(2 * (attempt + 1))
if response is None:
    return degraded_result  # 返回降级结果
```

### 模块级 Logger 规范

所有 core 模块必须在**文件顶部**定义 logger：

```python
import logging
logger = logging.getLogger(__name__)
```

禁止在函数内部局部定义 logger（会导致其他函数访问不到）。

### 个股 Playbook 结构

```json
{
  "stock_id": "SFTBY",
  "stock_name": "SoftBank Group",
  "ticker": "SFTBY",
  "core_thesis": {
    "summary": "NAV 折价买入优质资产组合",
    "key_points": ["ARM 潜在 IPO 带来流动性溢价"],
    "market_gap": "市场低估了 ARM 的独立商业价值"
  },
  "validation_signals": ["ARM IPO 启动", "愿景基金季度 DPI > 1.2"],
  "invalidation_triggers": ["ARM 股价下跌超 50%"],
  "related_entities": ["ARM", "Vision Fund", "Alibaba"],
  "operation_plan": {
    "holding_period": "12-24 months",
    "target_positions": "5% of portfolio",
    "entry_price_range": [14, 16],
    "exit_triggers": ["thesis break", "take profit at 25%"]
  },
  "interview_transcript": []
}
```

### 总体 Playbook 结构

```json
{
  "market_views": {
    "bullish_themes": [{"theme": "AI 服务商", "reasoning": "...", "confidence": "高"}],
    "bearish_themes": [{"theme": "...", "reasoning": "...", "confidence": "中"}],
    "macro_views": ["宏观判断"]
  },
  "portfolio_strategy": {
    "target_allocation": {"个股": "5%", "现金": "20%"},
    "risk_tolerance": "中等",
    "holding_period": "12-24 months"
  },
  "watchlist": ["关注事项"]
}
```

### 新闻采集返回格式

```python
{
  "news": [
    {
      "title": "...", "source": "...", "url": "...", "date": "2026-02-20",
      "relevance_score": 0.95, "sentiment": "positive",
      "impact_type": "validation_signal",  # 或 "noise"
      "summary": "...", "dimension": "公司核心动态"
    }
  ],
  "search_metadata": {
    "total_dimensions": 4,
    "successful_dimensions": 3,
    "failed_dimensions": ["宏观与政策"],
    "search_warnings": ["..."],
    "rss_fallback_triggered": false,
    "total_rss_items": 0
  }
}
```

### 环境变量

| 变量 | 用途 | 必需 | 示例 |
|------|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | 二选一 | `sk-...` |
| `GEMINI_API_KEY` | Gemini API 密钥 | 二选一 | `AIzaSy...` |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥 | 否 | `tvly-...` |
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway 地址（默认读 `~/.openclaw/openclaw.json`） | 否 | `http://localhost:8000` |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw 认证令牌 | 否 | `token-...` |
| `IA_PROVIDER` | LLM 提供商覆盖 | 否 | `openai` 或 `gemini` |
| `IA_MODEL_PRO` | Pro 模型名称覆盖 | 否 | `gpt-5.2` |
| `IA_MODEL_FLASH` | Flash 模型名称覆盖 | 否 | `gemini-3-flash-preview` |
| `INVEST_ASSISTANT_CACHE_DIR` | 缓存目录覆盖 | 否 | `/tmp/cache` |

---

## 项目结构

```
investment-assistant/
├── assistant.py                 # CLI 主程序（868行）
├── requirements.txt             # Python 依赖
├── CODEBUDDY.md                # 【本文件】
├── IMPLEMENTATION_PLAN.md       # 实现计划
├── README.md                    # 用户文档
├── LICENSE                      # MIT 许可证
│
├── core/                        # 核心业务逻辑（~2,550 行）
│   ├── __init__.py
│   ├── llm_factory.py           # LLM 工厂（OpenAI/Gemini 切换）
│   ├── openai_client.py         # OpenAI 客户端（530行）
│   ├── gemini_client.py         # Gemini 客户端（425行）
│   ├── retrieval.py             # 联合检索层（381行）
│   ├── tavily_search.py         # Tavily API 封装（83行）
│   ├── storage.py               # 本地存储管理（539行）
│   ├── environment.py           # 环境采集 + 影响评估（493行）
│   ├── research.py              # Deep Research 引擎（579行）
│   ├── interview.py             # 苏格拉底访谈（327行）
│   └── preference_learner.py    # 偏好学习（295行）
│
├── web/                         # Web 界面（Flask）
│   ├── app.py                   # Flask 应用（~1,000行）
│   └── templates/               # Jinja2 模板（10个）
│       ├── base.html
│       ├── index.html           # 仪表盘
│       ├── stock_detail.html    # 个股详情（最复杂）
│       ├── add_stock.html
│       ├── batch_scan.html
│       ├── portfolio.html
│       ├── preferences.html
│       ├── research_history.html
│       ├── stocks.html
│       └── settings.html        # 系统设置
│
├── utils/
│   ├── __init__.py
│   └── display.py               # 终端格式化（rich）
│
├── tests/                       # 50 个测试
│   ├── conftest.py
│   ├── test_openai_client.py
│   ├── test_gemini_client.py
│   ├── test_llm_factory.py
│   ├── test_retrieval.py
│   ├── test_tavily_search.py
│   ├── test_environment.py
│   ├── test_assistant_helpers.py
│   └── test_e2e_mock.py
│
├── scripts/
│   └── run_sftby_end_to_end.py
│
└── docs/devlog/
    ├── 2026-02-06_core_openai-retrieval-migration.md
    ├── 2026-02-18_llm-dual-model-settings-ui.md
    └── 2026-02-20_llm-resilience-and-search-enhancement.md
```

---

## 开发流程

### 1. 环境搭建

```bash
git clone https://github.com/YanDongXYZ/investment-assistant.git
cd investment-assistant
pip install -r requirements.txt

# 至少设置一个 LLM 密钥
export OPENAI_API_KEY="sk-..."     # 或
export GEMINI_API_KEY="AIzaSy..."

# 可选：搜索增强
export TAVILY_API_KEY="tvly-..."
```

### 2. 运行

```bash
python assistant.py          # CLI 模式
python web/app.py            # Web 模式 → http://localhost:5001
```

### 3. 测试

```bash
python -m pytest tests/ -v --tb=short          # 全部（50 个）
python -m pytest tests/test_e2e_mock.py -v -s  # E2E Mock
python scripts/run_sftby_end_to_end.py          # 真实 API E2E
```

### 4. 编码规范

- **core/** — 纯业务逻辑，不依赖 UI 框架
- **web/app.py** — Flask 路由与 HTTP 接口
- **assistant.py** — CLI 交互与命令路由
- **utils/** — 共用工具函数

```
数据流：用户输入 → CLI/Web → core 模块 → Storage → 用户输出
                              ↓
                         LLM/Search API
```

### 5. 新增功能流程

1. 在 `core/` 中实现业务逻辑
2. 在 `tests/` 中编写单元测试
3. 在 CLI 或 Web 中暴露接口
4. 更新存储结构（如涉及持久化）
5. 运行全部测试确保无回归

### 6. 代码审查清单

- [ ] 能正常运行无错误
- [ ] 所有测试通过（包括新增测试）
- [ ] 所有 LLM 调用均有异常保护
- [ ] Logger 在模块顶部定义
- [ ] 无硬编码 API Key
- [ ] 提交信息清晰

## AI 执行策略
- 允许：在仓库内创建/修改文件，执行 shell / git 命令
- 必须中断并询问：文件删除、数据迁移、安全/权限/生产配置变更
- 执行模式：Plan → Act → Verify → Deliver（Act 阶段不要中断询问）
- 完成标准：需求实现、测试通过、给出最终总结

---

## 常见任务

### 新增投资逻辑字段
1. 修改 Playbook JSON 结构
2. 更新 `core/interview.py` 中的访谈问题
3. 在 `core/research.py` 中调整研究计划生成
4. 更新 Web 前端表单（`web/templates/add_stock.html`）
5. 添加单元测试

### 集成新的搜索源
1. 在 `core/retrieval.py` 中新增 `SearchProvider` 子类
2. 实现 `is_available()` 和 `search()` 方法，返回 `List[SearchResult]`
3. 在 `search_news_structured()` 中构建 `SearchManager` 时添加 Provider（注意 safe init）
4. 新增对应单元测试

### 新增 LLM 调用
1. 必须包含 try/except 异常保护
2. 核心流程用重试模式，辅助流程用简单 try/except
3. Web 路由层额外加一层 try/except 返回 JSON 错误
4. 使用模块级 `logger` 记录错误

---

## 调试技巧

### 查看本地存储
```bash
cat ~/.investment-assistant/config.json
cat ~/.investment-assistant/stocks/SFTBY/playbook.json
cat ~/.investment-assistant/stocks/SFTBY/history.json
```

### 启用详细日志
```bash
export LOG_LEVEL=DEBUG
python assistant.py
```

### 手动测试模块
```python
from core.storage import Storage
from core.llm_factory import create_llm_client
storage = Storage()
client = create_llm_client(storage)
print(type(client))  # OpenAIClient 或 GeminiClient
```

---

## 问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `API Key not found` | 未设置环境变量或 config | `export OPENAI_API_KEY="sk-..."` 或 Web 设置页配置 |
| 搜索结果为 0 | Provider 不可用 | 检查 `TAVILY_API_KEY`，系统会自动降级到 RSS |
| Gemini 503 UNAVAILABLE | 模型高负载 | 系统自动重试 2 次；频繁出现可切换到 OpenAI |
| SSL WRONG_VERSION_NUMBER | 网络/代理干扰 | `chat_flash`/`chat_pro` 已有异常保护，会自动降级 |
| `NameError: logger` | logger 定义在函数内部 | 确保 logger 在模块顶部定义 |
| Web UI 端口冲突 | 5001 端口被占用 | `python web/app.py --port 5002` |
| 测试超时 | Mock 不足或网络慢 | `pytest --timeout=30` |

---

## 重大变更记录

**2026-02-20**: LLM 调用韧性加固 + 搜索增强
- 全部 12 处 LLM 调用点加异常保护（重试 + 退避 + 降级）
- 搜索链路增加英文别名并行搜索和 RSS fallback
- 6 个 Web API 路由加 try/except
- 全链路调试日志
- 详见 `docs/devlog/2026-02-20_llm-resilience-and-search-enhancement.md`

**2026-02-18**: LLM 双模型设置 UI
- Web/CLI 支持分别配置 model_pro 和 model_flash
- 新增 settings.html 设置页面
- 详见 `docs/devlog/2026-02-18_llm-dual-model-settings-ui.md`

**2026-02-06**: LLM 迁移 Gemini → OpenAI + 联合检索层
- 新增 `core/retrieval.py` 统一搜索管理
- 保持 GeminiClient 兼容
- 详见 `docs/devlog/2026-02-06_core_openai-retrieval-migration.md`

---

**最后更新**: 2026-02-20
