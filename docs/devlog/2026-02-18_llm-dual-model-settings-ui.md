# 2026-02-18: LLM 双模型分流与系统配置页

## 背景
- 需要 Pro 用于深度分析、Flash 用于快速搜索/访谈。
- 模型/Key 设置从偏好页迁移到独立“系统配置”页面。

## 变更
- LLM 双模型配置：新增 `llm_model_pro/llm_model_flash` 读写与解析，支持 OpenAI/Gemini；CLI 增加设置 Pro/Flash 模型命令。
- 客户端分流：深度分析走 Pro（影响评估/深度研究/偏好学习/文件解析），访谈与搜索走 Flash。
- 新增系统配置页 `/settings`，新增 `/api/config/keys`（掩码展示、不可清空）。
- UI 调整：偏好页移除模型设置；导航新增“系统配置”入口。
- Playbook 展示兼容：`portfolio`/`index` 适配 `bullish_themes` 与 stocks 列表展示。
- Web 默认端口更新为 5001，并同步 README。

## 影响范围
- 核心：`core/openai_client.py`、`core/gemini_client.py`、`core/llm_factory.py`、`core/storage.py`
- 业务：`core/environment.py`、`core/research.py`、`core/interview.py`、`core/preference_learner.py`
- Web：`web/app.py`、`web/templates/settings.html`、`web/templates/base.html`、`web/templates/preferences.html`、`web/templates/portfolio.html`、`web/templates/index.html`
- 文档与脚本：`README.md`、`scripts/run_sftby_end_to_end.py`
- 测试：`tests/test_gemini_client.py`、`tests/test_llm_factory.py`、`tests/test_openai_client.py`

## 测试
- `python -m pytest tests -v --tb=short`
