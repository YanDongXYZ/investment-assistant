# 投资研究助手 - CODEBUDDY.md

## 项目概述

投资研究助手（Investment Research Assistant）是一个基于 AI 的个人投资研究系统，帮助投资者：
- 系统化管理投资逻辑（Playbook 系统）
- 追踪市场变化与信息关联（环境采集）
- 生成深度研究报告（Deep Research 引擎）
- 学习和优化投资决策（偏好学习系统）

**当前技术栈：** Python 3.9+ | Flask 3.0+ | OpenAI GPT-5.2 | Tavily + OpenClaw 联合检索

---

## 核心模块与职责

### 1. **CLI 入口** (`assistant.py`)
- **职责**：多行交互式命令行界面，支持 JSON 编辑和命令路由
- **主要功能**：
  - Playbook 管理（创建、编辑、查看）
  - 苏格拉底访谈系统（引导用户完善投资逻辑）
  - 研究执行与历史查看
  - 配置管理

### 2. **Web UI** (`web/app.py`)
- **职责**：Flask Web 界面，提供仪表盘和可视化
- **主要路由**：
  - `/` - 首页仪表盘
  - `/stock/<stock_id>` - 个股详情
  - `/batch_scan` - 批量扫描持仓
  - `/portfolio` - 总体 Playbook 编辑
  - `/preferences` - 用户偏好管理
  - `/research_history` - 研究历史查看

### 3. **LLM 客户端** (`core/openai_client.py`)
- **职责**：OpenAI API 通信，支持三种工作模式
- **接口**：
  - `chat()` - 普通对话
  - `chat_with_system()` - 自定义系统提示对话
  - `search_news_structured()` - 结构化新闻搜索与分析
- **依赖**：`OPENAI_API_KEY` 环境变量

### 4. **检索层** (`core/retrieval.py`)
- **职责**：统一搜索管理，支持多源检索降级
- **核心类**：
  - `SearchManager` - 统一入口，决策使用哪个提供商
  - `TavilyProvider` - Tavily API（优先）
  - `OpenClawWebSearchProvider` - Brave Search（via OpenClaw Gateway）
  - 搜索结果缓存：`~/.investment-assistant/cache/search/`
- **关键约定**：禁止直接调用 Brave HTTP API，必须通过 OpenClaw Gateway

### 5. **环境采集** (`core/environment.py`)
- **职责**：多维度新闻搜索与影响评估
- **返回格式**：`Dict{"news": List[Dict], "search_metadata": Dict}`
- **三维评估**：
  - 信号检测 - 这是关键市场信号吗？
  - 多角度搜索 - 从竞争对手、产业链、监管等多维搜索
  - 影响分析 - 对投资逻辑的正面/负面影响程度

### 6. **Deep Research 引擎** (`core/research.py`)
- **职责**：生成可执行的研究计划与深度报告
- **流程**：
  1. 解析投资逻辑的关键假设
  2. 生成针对性研究计划（包含假设验证、场景分析）
  3. 执行搜索并收集信息
  4. 编写结构化研究报告
- **输出**：JSON 格式报告，包含验证结果与建议

### 7. **苏格拉底访谈** (`core/interview.py`)
- **职责**：对话式指导用户完善 Playbook
- **核心问题**：
  - 你为什么买？（核心论点）
  - 什么说明你对了？（验证信号）
  - 什么说明你错了？（失效条件）
  - 相关的关键实体有哪些？（扩展搜索）
- **输出**：结构化 Playbook JSON

### 8. **偏好学习系统** (`core/preference_learner.py`)
- **职责**：记录决策历史，学习用户偏好，优化建议
- **学习维度**：
  - 信息来源偏好
  - 分析深度偏好
  - 风险承受度
  - 决策周期模式
- **应用**：调整系统搜索范围、报告结构、建议力度

### 9. **本地存储** (`core/storage.py`)
- **职责**：管理所有用户数据持久化
- **数据位置**：`~/.investment-assistant/`
  ```
  ~/.investment-assistant/
  ├── config.json                # 全局配置（API Key 等）
  ├── portfolio_playbook.json    # 总体投资框架
  ├── user_preferences.json      # 用户偏好规则
  ├── stocks/{stock_id}/
  │   ├── playbook.json          # 个股投资逻辑
  │   ├── history.json           # 研究历史
  │   └── uploads/               # 用户上传的研报、文件
  └── logs/                      # 日志文件
  ```
- **关键约定**：配置文件 key 为 `openai_api_key`（向后兼容 `gemini_api_key`）

### 10. **Tavily 检索** (`core/tavily_search.py`)
- **职责**：Tavily API 薄包装
- **依赖**：`TAVILY_API_KEY` 环境变量（可选；无则降级 RSS）

### 11. **显示层** (`utils/display.py`)
- **职责**：终端格式化输出（使用 `rich` 库）
- **功能**：表格、彩色文本、进度条、代码块等

---

## 关键约定 & 设计模式

### Playbook 结构（JSON 格式）

```json
{
  "stock_id": "SFTBY",
  "stock_name": "SoftBank Group",
  "core_thesis": "NAV 折价买入优质资产组合",
  "key_points": [
    "ARM 潜在 IPO 带来流动性溢价",
    "愿景基金 I 已接近成熟，持有现金充足"
  ],
  "market_view_diff": "市场低估了 ARM 的独立商业价值",
  "validation_signals": {
    "bullish": ["ARM IPO 启动", "愿景基金季度 DPI > 1.2"],
    "bearish": ["ARM 客户流失", "SFG 股价跌超折价幅度"]
  },
  "failure_conditions": [
    "ARM 股价下跌超 50%",
    "愿景基金连续 2 个季度亏损"
  ],
  "related_entities": ["ARM", "Vision Fund", "Alibaba", "Yahoo Japan"],
  "operation_plan": {
    "holding_period": "12-24 months",
    "target_positions": "5% of portfolio",
    "entry_price_range": [14, 16],
    "exit_triggers": ["thesis break", "take profit at 25%"]
  }
}
```

### 新闻采集返回格式

```python
{
  "news": [
    {
      "title": "ARM Announces IPO Plans",
      "source": "Reuters",
      "url": "...",
      "date": "2026-02-18",
      "relevance_score": 0.95,
      "sentiment": "positive",
      "impact_type": "validation_signal",  # 或 "noise"
      "summary": "..."
    }
  ],
  "search_metadata": {
    "total_results": 42,
    "search_time_seconds": 2.3,
    "coverage_dimensions": ["company_news", "competitor_move", "regulatory"]
  }
}
```

### 环境变量（`.env` 或 shell 中设置）

| 变量 | 用途 | 必需 | 示例 |
|------|------|------|------|
| `OPENAI_API_KEY` | OpenAI API 访问密钥 | 是 | `sk-...` |
| `TAVILY_API_KEY` | Tavily 搜索 API 密钥 | 否 | `tvly-...` |
| `OPENCLAW_GATEWAY_URL` | OpenClaw Gateway 服务器地址（默认读 `~/.openclaw/openclaw.json`） | 否 | `http://localhost:8000` |
| `OPENCLAW_GATEWAY_TOKEN` | OpenClaw 认证令牌 | 否 | `token-...` |

---

## 项目结构

```
investment-assistant/
├── assistant.py                 # 【入口】CLI 主程序
├── requirements.txt             # 【配置】Python 依赖
├── CODEBUDDY.md                # 【本文件】
├── CLAUDE.md                    # 【开发指南】原项目文档
├── README.md                    # 【用户文档】功能说明
├── LICENSE                      # MIT 许可证
├── .gitignore                   # Git 配置
│
├── core/                        # 【核心模块】投资逻辑引擎
│   ├── __init__.py
│   ├── openai_client.py         # LLM 客户端
│   ├── retrieval.py             # 联合检索层（Tavily + OpenClaw）
│   ├── tavily_search.py         # Tavily API 封装
│   ├── storage.py               # 本地存储管理
│   ├── environment.py           # 环境采集（新闻搜索、影响评估）
│   ├── research.py              # Deep Research 引擎
│   ├── interview.py             # 苏格拉底访谈系统
│   └── preference_learner.py    # 偏好学习系统
│
├── web/                         # 【Web 界面】Flask 应用
│   ├── app.py                   # 【入口】Flask 应用
│   └── templates/               # HTML 前端模板
│       ├── base.html            # 基础模板
│       ├── index.html           # 首页仪表盘
│       ├── stock_detail.html    # 个股详情（最复杂）
│       ├── add_stock.html       # 添加股票
│       ├── batch_scan.html      # 批量扫描
│       ├── portfolio.html       # 总体 Playbook 编辑
│       ├── preferences.html     # 用户偏好管理
│       ├── research_history.html # 研究历史
│       └── stocks.html          # 股票列表
│
├── utils/                       # 【工具函数】
│   ├── __init__.py
│   └── display.py               # 终端格式化输出
│
├── tests/                       # 【测试】pytest 单元 + E2E 测试
│   ├── conftest.py              # pytest 配置与 Fixtures
│   ├── test_openai_client.py    # LLM 客户端单元测试
│   ├── test_retrieval.py        # 检索层单元测试
│   ├── test_environment.py      # 环境采集单元测试
│   ├── test_tavily_search.py    # Tavily 单元测试
│   ├── test_assistant_helpers.py # 辅助函数单元测试
│   └── test_e2e_mock.py         # E2E Mock 集成测试
│
├── scripts/                     # 【自动化脚本】
│   └── run_sftby_end_to_end.py  # CI/cron 端到端测试
│
└── docs/                        # 【文档】
    └── devlog/
        └── 2026-02-06_core_openai-retrieval-migration.md
```

---

## 开发流程

### 1. 环境搭建

```bash
# 克隆项目
git clone https://github.com/YanDongXYZ/investment-assistant.git
cd investment-assistant

# 安装依赖
pip install -r requirements.txt

# 设置 API 密钥
export OPENAI_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."  # 可选
```

### 2. 运行模式

```bash
# 启动 CLI 主程序
python assistant.py

# 启动 Web UI（访问 http://localhost:5000）
python web/app.py

# 运行测试
python -m pytest tests/ -v --tb=short
python -m pytest tests/test_openai_client.py -v
python -m pytest tests/test_e2e_mock.py -v
python scripts/run_sftby_end_to_end.py
```

### 3. 编码规范

#### 模块职责分工
- **core/** - 纯业务逻辑，不依赖 UI 框架
- **web/app.py** - Flask 路由与 HTTP 接口
- **assistant.py** - CLI 交互与命令路由
- **utils/** - 共用工具函数

#### 数据流向
```
用户输入 → CLI/Web → core 模块 → Storage → 用户输出
         ↓
      LLM/Search API
```

#### 新增功能流程
1. **在 core/ 中实现业务逻辑**（关键功能）
2. **在 tests/ 中编写单元测试**（覆盖主路径）
3. **在 CLI 或 Web 中暴露接口**（用户可调用）
4. **更新存储结构**（如果涉及持久化）
5. **运行全部测试**（确保无回归）

### 4. 测试驱动开发（TDD）

遵循红-绿-重构流程：

```bash
# 1. 编写测试（红色 - 测试失败）
# 编辑 tests/test_xxx.py，定义预期行为

# 2. 编写实现（绿色 - 测试通过）
# 编辑 core/xxx.py，实现功能直至测试通过

# 3. 运行全部测试（确保无回归）
python -m pytest tests/ -v --tb=short

# 4. 重构（改进代码质量）
# 优化实现，保持测试通过

# 5. 提交代码
git add .
git commit -m "feat: 描述功能"
```

### 5. 代码审查清单

- [ ] 能否编译/运行无错误
- [ ] 所有测试通过（包括新增测试）
- [ ] 代码风格符合项目规范
- [ ] 没有代码 linter 或 formatter 警告
- [ ] 提交信息清晰（说明"为什么"，不只是"做了什么"）
- [ ] 无硬编码的 API Key 或密钥
- [ ] 数据存储位置符合约定

## AI 执行策略（来自 CLAUDE.md）
- 允许：在仓库内创建/修改文件，执行必要的 shell / git 命令
- 必须中断并询问：文件删除、数据迁移、安全/权限/生产配置变更
- 执行模式：Plan → Act → Verify → Deliver（Act 阶段不要中断询问）
- 完成标准：需求实现、测试通过、给出最终总结

---

## 常见任务

### 新增投资逻辑字段
1. 修改 `Playbook` JSON 结构（docs 中更新示例）
2. 更新 `core/interview.py` 中的访谈问题
3. 在 `core/research.py` 中相应调整研究计划生成
4. 更新 Web 前端表单（`web/templates/add_stock.html`）
5. 添加单元测试验证新字段序列化/反序列化

### 集成新的搜索源
1. 在 `core/retrieval.py` 中新增 `Provider` 子类
2. 实现 `search()` 方法，返回统一格式
3. 在 `SearchManager` 中添加降级逻辑
4. 新增对应单元测试
5. 更新环境变量文档

### 优化 LLM 调用效率
1. 分析 `core/openai_client.py` 中的 prompt 设计
2. 考虑结果缓存（见 `core/storage.py` 的缓存机制）
3. 利用结构化输出（JSON mode）减少解析成本
4. 运行性能测试验证改进

---

## 调试技巧

### 查看本地存储
```bash
# 查看配置
cat ~/.investment-assistant/config.json

# 查看某只股票 Playbook
cat ~/.investment-assistant/stocks/SFTBY/playbook.json

# 查看研究历史
cat ~/.investment-assistant/stocks/SFTBY/history.json
```

### 启用详细日志
```bash
# Python 日志级别设置（如果有日志记录）
export LOG_LEVEL=DEBUG
python assistant.py
```

### Mock 测试运行
```bash
# 运行不调用真实 API 的 Mock 测试
python -m pytest tests/test_e2e_mock.py -v -s
```

### 手动测试某个模块
```bash
# 启动 Python 交互式 shell
python3

# 导入并测试
from core.storage import StorageManager
from core.openai_client import OpenAIClient
storage = StorageManager()
config = storage.load_config()
print(config)
```

---

## 性能与优化

### 搜索缓存
- 位置：`~/.investment-assistant/cache/search/`
- 策略：按搜索查询 hash 缓存结果，避免重复调用
- TTL：可在 `core/retrieval.py` 中配置

### LLM 调用优化
- 使用结构化输出（JSON mode）
- 批量操作时缓存系统提示
- 模型选择以项目 OpenAI 配置为准（见 `core/openai_client.py`）

### Web UI 性能
- 前端静态资源缓存
- API 响应异步化（如 Deep Research 报告生成）
- 搜索结果分页展示

---

## 最近重大变更

**2026-02-06**: LLM 迁移 Gemini → OpenAI GPT-5.2 + 联合检索层
- 原因：OpenAI API 稳定性更好，模型性能更强
- 变更：新增 `core/retrieval.py` 统一搜索管理
- 存档：见 `docs/devlog/2026-02-06_core_openai-retrieval-migration.md`
- 兼容性：保持配置文件向后兼容（`gemini_api_key` → `openai_api_key`）

---

## 问题排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `OPENAI_API_KEY not found` | 未设置环境变量 | `export OPENAI_API_KEY="sk-..."` |
| 搜索结果为空 | Tavily API 无效或配额耗尽 | 检查 `TAVILY_API_KEY`，尝试 OpenClaw 降级 |
| 本地存储不同步 | 多进程竞态条件 | 检查 `core/storage.py` 的文件锁机制 |
| Web UI 无法启动 | 端口 5000 被占用 | `python web/app.py --port 5001` |
| 测试超时 | Mock 数据不足或网络慢 | 增加 pytest timeout：`pytest --timeout=30` |

---

## 联系与反馈

- **项目仓库**：https://github.com/YanDongXYZ/investment-assistant
- **原始文档**：见 `README.md` 和 `CLAUDE.md`
- **提问与反馈**：在 GitHub Issues 中提出

---

**最后更新**: 2026-02-18 | 作者：Investment Assistant Dev Team
