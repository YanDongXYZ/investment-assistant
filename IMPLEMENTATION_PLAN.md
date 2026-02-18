## 阶段 1: LLM 配置与工厂
**目标**: 新增 LLM provider/model 配置与工厂入口，支持按配置创建客户端。
**成功标准**: 可从 config/env 读取 provider/model；OpenAI 默认模型不变。
**测试**: 新增/调整配置与工厂单测。
**状态**: 已完成

## 阶段 2: Gemini 客户端接入
**目标**: 新增 GeminiClient，兼容 chat/chat_with_system/search_news_structured 接口。
**成功标准**: gemini-3-pro-preview / gemini-3-flash-preview 可被创建并调用。
**测试**: 新增 GeminiClient 单测（mock 官方 SDK）。
**状态**: 已完成

## 阶段 3: CLI/Web 模型切换
**目标**: CLI 与 Web 偏好页支持切换 provider/model。
**成功标准**: 切换后新客户端生效；UI 显示当前配置。
**测试**: 调整 CLI/Web 相关测试。
**状态**: 已完成

## 阶段 4: 依赖与回归
**目标**: 更新依赖并保持现有功能与测试稳定。
**成功标准**: 现有测试通过；OpenAI 路径仍可用。
**测试**: 运行核心 pytest 用例。
**状态**: 已完成
