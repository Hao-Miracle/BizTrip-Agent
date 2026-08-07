# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/lang/zh-CN/spec/v2.0.0.html).

---

## [Unreleased]

### 新增

- **Windows 一键测试版** — GitHub Actions 自动生成无需 Python、Git 或命令行的单文件 EXE
- **Windows 本地持久化** — 配置保存在 `%LOCALAPPDATA%\BizTripAgent`，报销文件保存在“文档\BizTrip Agent”
- **本地程序控制** — Web 页面可以打开报销文件夹并安全停止程序
- **报销包验收结论** — Web 首页和审阅页显示“可以提交”或“暂不建议提交”
- **完整性检查** — 检查金额、日期、供应商、原件和行程归属
- **重复与冲突检查** — 检测重复原件、重复订单号/发票号及同一单号数据冲突
- **验收结果留档** — JSON 保存完整记录数、待处理记录数和问题数

### 修复

- 多 PDF 机票邮件拆分后，每条记录只关联自己的 PDF，避免重复原件误报

## [0.1.1] - 2026-07-05

### 新增

#### 文档体系
- **安装指南** — `docs/installation.md`，详细的安装和配置步骤，支持多邮箱服务商
- **使用指南** — `docs/usage.md`，功能说明、输出格式、命令行参数
- **常见问题 FAQ** — `docs/faq.md`，使用相关、数据准确、技术问题、贡献指南
- **Agent Skills 使用指南** — `docs/skills.md`，各平台 Skill 配置方法
- **贡献指南** — `CONTRIBUTING.md`，代码规范、提交规范、贡献方式

#### GitHub 配置
- **LICENSE** — MIT 许可证正式文件
- **Issue 模板** — Bug 报告模板 + 功能建议模板
- **PR 模板** — Pull Request 提交模板
- **CHANGELOG** — 遵循 Keep a Changelog 规范的变更日志

### 改进

- **README 产品化重写** — 居中标题、动态徽章、痛点引入、核心能力展示、快速上手、输出效果、完整导航
- **仓库结构优化** — 新增 `docs/` 目录分离文档，`.github/` 目录规范 GitHub 配置
- **版本号徽章** — 使用 GitHub 动态版本徽章

### 路线图补充
- Phase 3 团队版（多人协作 + 审批流 + 财务系统对接）加入路线图

---

## [0.1.0] - 2026-07-05

### 新增

#### 规则引擎（Phase 1）
- **IMAP 邮箱连接** — 支持 QQ/163/126/Gmail/Outlook 全平台邮箱，自动推断 IMAP 服务器
- **智能分类** — 域名匹配 + 关键词匹配双规则，分类准确率高
- **8 平台解析器** — 机票、火车票、酒店、网约车、发票、门票全覆盖
  - 机票：去哪儿、携程、飞猪、航司邮件
  - 火车票：12306、智行
  - 酒店：华住、Booking、携程、美团
  - 网约车：滴滴、高德（曹操/T3/及时/喜行等）
  - 发票：智慧发票(cresvtv.cn)、票根(txffp.com)
  - 门票：大麦
- **三 Sheet Excel 报表** — 报销总览 + 费用明细 + 按供应商统计
- **附件自动归档** — PDF/ZIP 原件自动下载，每条记录可溯源
- **金额提取优先级** — PDF 文件名 > 价税合计 > 合计...元 > ¥ 兜底

#### Agent 引擎（Phase 1.5）
- **LLM 分类** — 智能识别差旅邮件，置信度不足自动降级规则引擎
- **LLM 提取** — 结构化提取金额/日期/路线/订单号，关键字段缺失降级正则
- **出差聚合** — 按同一时间段+同一目的地归并为一次出差
- **多模型支持** — 兼容任何 OpenAI 协议的服务商（DeepSeek、通义千问、GLM、Kimi、Ollama 等）
- **零配置降级** — 不配 API Key 完全可用，自动降级纯规则引擎

#### Agent Skills
- **5 个 TRAE IDE Skill** — fetch-emails / classify-emails / extract-emails / generate-report / agent-report
- **5 个通用 Agent Skill** — Markdown 格式，支持 Claude Code / Cursor / GitHub Copilot / Windsurf / TRAE IDE

#### 知识库
- **LLM Wiki 知识库** — 产品定义、竞品分析、架构设计、功能规格、决策记录、任务拆解
- **SOUL.md** — Agent 身份定义、核心原则、工作流、边界

### 设计原则

1. **数据准确是底线** — 每一行金额、每一条日期、每一个路线都与邮件原文一致
2. **规则优先，零 API Key 可运行** — 默认基于规则引擎，零成本运行
3. **隐私优先** — 所有邮件数据仅在用户本地处理，只读邮箱权限
4. **两层可用** — 零配置规则引擎保证基本可用，配 LLM 升级智能提取

---

[0.1.1]: https://github.com/Hao-Miracle/BizTrip-Agent/releases/tag/v0.1.1
[0.1.0]: https://github.com/Hao-Miracle/BizTrip-Agent/releases/tag/v0.1.0
