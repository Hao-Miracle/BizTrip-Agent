<div align="center">

# BizTrip Agent

**个人出差与旅行的行程与报销信息自动归集工具**

授权邮箱，AI 自动扫描确认邮件，提取结构化信息。  
出差中看行程，出差后一键生成报销表。

<p>
  <a href="https://github.com/Hao-Miracle/BizTrip-Agent/releases">
    <img src="https://img.shields.io/github/v/release/Hao-Miracle/BizTrip-Agent?style=flat-square" alt="release">
  </a>
  <img src="https://img.shields.io/badge/python-3.8+-yellow?style=flat-square" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="license">
  <a href="CHANGELOG.md">
    <img src="https://img.shields.io/badge/CHANGELOG-8A2BE2?style=flat-square&logo=keep-a-changelog&logoColor=white" alt="changelog">
  </a>
  <a href="https://github.com/Hao-Miracle/BizTrip-Agent/stargazers">
    <img src="https://img.shields.io/github/stars/Hao-Miracle/BizTrip-Agent?style=flat-square&color=orange" alt="stars">
  </a>
</p>

<p>
  <a href="#-快速开始">快速开始</a> ·
  <a href="docs/usage.md">使用文档</a> ·
  <a href="docs/faq.md">常见问题</a> ·
  <a href="CHANGELOG.md">更新日志</a> ·
  <a href="CONTRIBUTING.md">贡献指南</a>
</p>

</div>

---

## ✨ 为什么用它？

每次出差回来，是不是要花几个小时：

- 📧 翻几十封邮件找订单和发票
- 📋 手动录入机票、酒店、打车费用
- 🔍 核对金额和日期，生怕出错
- 📊 整理成 Excel 报销表

**BizTrip Agent 帮你全自动搞定：**

> 授权邮箱 → 自动扫描 → 提取结构化信息 → 生成报销 Excel + 行程卡  
> **全程本地处理，只读不写，隐私安全**

---

## 🎯 核心能力

| 能力 | 说明 |
|------|------|
| **📧 多邮箱支持** | QQ / 163 / 126 / Gmail / Outlook，标准 IMAP 协议 |
| **🤖 智能分类** | 域名匹配 + 关键词 + LLM 三层识别，准确率高 |
| **📊 结构化提取** | 金额 / 日期 / 路线 / 订单号 / 发票号，全字段提取 |
| **🧳 出差聚合** | 自动按时间段+目的地归并同一次出差 |
| **📑 Excel 报表** | 报销总览 + 费用明细 + 按供应商统计，三 Sheet 齐全 |
| **📁 附件归档** | 原始 PDF / ZIP 自动下载，每条记录可溯源 |
| **🧠 LLM 增强** | 可选 AI 增强，提升复杂场景识别率 |
| **🔒 隐私优先** | 全部本地处理，只读邮箱权限，数据不出你的电脑 |

---

## 🏆 支持的平台

### ✈️ 机票
去哪儿 · 携程 · 飞猪 · 各航司官网邮件

### 🚄 火车票
12306 · 智行

### 🏨 酒店
华住 · Booking · 携程 · 美团

### 🚕 网约车
滴滴 · 高德（曹操 / T3 / 及时 / 喜行 等）

### 🧾 发票
智慧发票 (cresvtv.cn) · 票根 (txffp.com)

### 🎫 门票
大麦

> 新增平台只需加一行域名规则，欢迎 [贡献代码](CONTRIBUTING.md)！

---

## 🚀 快速开始

### 1. 先确认有 Python

```bash
python3 --version
```

如果提示找不到 `python3`，或版本低于 `3.8`，先安装 Python 3.8+。
macOS 用户可以从 [python.org](https://www.python.org/downloads/) 安装，或使用 Homebrew：

```bash
brew install python
```

### 2. 一条命令安装并启动

```bash
git clone https://github.com/Hao-Miracle/BizTrip-Agent.git && cd BizTrip-Agent && python3 -m venv .venv && .venv/bin/python -m pip install -e . && .venv/bin/biztrip web
```

这条命令会自动安装项目需要的 Python 依赖。它不会替你安装 Python 本身，也不会替你生成邮箱授权码。

### 3. 首次配置邮箱

Web 页面打开后，按“第一次使用”提示操作：

1. 打开邮箱设置，开启 IMAP/SMTP 服务
2. 生成邮箱授权码或应用专用密码，不要使用登录密码
3. 在页面填写邮箱账号和授权码，点击保存账号

它会打开本地页面。账号只配置一次；填写本次报销期间后点击“开始生成”，系统会自动选择 IMAP 服务器并生成报销包。
页面只显示准备状态和首次使用指引，不会展示邮箱授权码或 API Key。
真实扫描会在后台运行，页面会显示任务状态、错误原因和生成文件。

### 4. 以后再次启动

```bash
cd BizTrip-Agent && .venv/bin/biztrip web
```

### 5. 先跑 Demo（不需要邮箱）

不熟悉命令行参数时，先用引导模式：

```bash
biztrip wizard
```

按提示选择生成 Demo、重新生成报表，或检查本地环境。

```bash
biztrip demo
```

这会用虚构差旅数据在 `output/` 目录生成一份示例 Excel，先确认工具链可用。

想先看可审阅页面：

```bash
biztrip demo --review
```

### 4. 配置邮箱

```bash
biztrip init
# 编辑 .env，填入邮箱和授权码
```

> 详细配置指南见 [安装文档](docs/installation.md)

### 5. 扫描真实邮箱

```bash
biztrip scan
```

运行后按提示输入日期范围，直接回车扫描最近 60 封邮件。

也可以直接传参数，适合重复运行或自动化：

```bash
biztrip scan --start 2026-07-01 --end 2026-07-29
biztrip scan --count 100 --no-llm
biztrip scan --output-dir output/monthly
biztrip scan --review
```

> 旧入口仍可用：`python3 phase1/generate_report.py` 或 `python3 phase2/agent_report.py`。

### 6. 运行测试

```bash
pip install -e ".[test]"
pytest
```

测试使用虚构样本，不会连接邮箱。

---

## 📊 输出效果

运行后在 `output/` 目录生成：

```
output/
├── 差旅汇总_20260705_143022.xlsx    ← 三 Sheet Excel 报表
├── records_20260705_143022.json      ← 系统留档（用于复查/再生成）
└── 附件/                        ← 原始 PDF/ZIP 原件
    ├── 机票/
    ├── 火车票/
    ├── 酒店/
    ├── 网约车/
    └── 发票/
```

### Excel 报表结构

| Sheet | 内容 |
|-------|------|
| **报销总览** | 出差行程汇总 + 总额卡片 + 按类别汇总（分类配色） |
| **费用明细** | 所有记录按日期排序，最高金额红色高亮，标注提取方法 |
| **按供应商** | 各平台消费排名，隔行配色 |

`records_YYYYMMDD_HHMMSS.json` 是系统留档，普通使用只需要打开 Excel 和审阅页。文件名带生成时间，同一天重复扫描不会覆盖旧结果。

从 JSON 重新生成报表：

```bash
biztrip rebuild output/records_20260705_143022.json --review
```

---

## 🧠 LLM 增强（可选）

默认不需要配置 LLM，规则模式可以完整生成报销包。想增强复杂邮件识别时，在 Web 页面展开“高级配置”，填写 `LLM API Key` 即可；Base URL 和 Model 留空时默认使用 DeepSeek。

高级用户也可以手动配置任意兼容 OpenAI 协议的服务商（含本地模型）：

```env
# DeepSeek（推荐，中文好）
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

# Ollama 本地模型（完全免费，零联网）
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b
```

更多服务商（通义千问 / GLM / Kimi / 火山引擎）配置见 [.env.example](.env.example)。

### 降级策略

```
🧠 LLM 分类 → 置信度不足 → 📋 域名匹配兜底
🧠 LLM 提取 → 关键字段缺失 → 📋 正则提取兜底
🧠 LLM 聚合 → 调用失败     → 📋 规则聚合兜底
```

**不配 API Key 完全可用**，自动降级纯规则引擎，零成本。

### 成本参考

| 模型 | 一次扫描（~5 封差旅邮件） |
|------|--------------------------|
| DeepSeek V3 | < 0.05 元 |
| GLM-4-Flash | 0 元（免费额度） |
| Ollama 本地 | 0 元 |

---

## 🧩 Agent Skills（多平台支持）

项目内置 5 个 AI Agent Skill，不绑定任何特定 IDE。`skills/` 目录下的 `.md` 文件是通用格式，**Claude Code、Cursor、GitHub Copilot、Windsurf、TRAE IDE** 等均可使用。

| Skill | 功能 | 依赖 |
|-------|------|------|
| **fetch-emails** | IMAP 连接邮箱，获取邮件列表 | `python-dotenv` |
| **classify-emails** | 域名+关键词双规则分类差旅邮件 | `python-dotenv` |
| **extract-emails** | 多平台解析器，提取结构化信息 | `python-dotenv PyPDF2` |
| **generate-report** | 全链路 → 三 Sheet Excel + 附件归档 | `python-dotenv PyPDF2 openpyxl` |
| **agent-report** | LLM 增强版：智能分类+提取+出差聚合 | 以上全部 + `openai` |

> 详细使用说明见 [Agent Skills 文档](docs/skills.md)

---

## 🏗 项目架构

```
BizTrip-Agent/
├── phase1/             ← 规则引擎（零依赖，必装）
│   ├── fetch_emails.py      IMAP 邮箱连接
│   ├── classify_emails.py   规则分类（域名+关键词）
│   ├── extract_emails.py    结构化提取（正则+PDF）
│   └── generate_report.py   全链路输出（Excel+附件）
├── phase2/             ← Agent 引擎（LLM 增强，可选）
│   ├── llm_classify.py      LLM 路由分类 + 规则降级
│   ├── llm_extract.py       LLM 专用提取 + 正则降级
│   ├── llm_aggregate.py     LLM 出差聚合 + 规则兜底
│   └── agent_report.py      Agent 主入口
├── skills/             ← 通用 Agent Skill（.md 格式）
├── .trae/skills/       ← TRAE IDE 专用 Skill
├── docs/               ← 使用文档
├── wiki/               ← 知识库（产品/架构/决策/规格）
├── raw/                ← 原始需求文档
├── .env.example        ← 配置模板
├── CHANGELOG.md        ← 变更日志
├── CONTRIBUTING.md     ← 贡献指南
├── LICENSE             ← MIT 许可证
└── README.md
```

---

## 💡 设计原则

1. **数据准确是底线** — 每一行金额、每一条日期都与邮件原文一致
2. **规则优先，零 API Key 可运行** — 默认基于规则引擎，零成本
3. **两层可用** — 零配置保证基本可用，配 LLM 升级智能提取
4. **隐私优先** — 所有数据本地处理，只读邮箱权限
5. **附件可溯源** — 原始 PDF/ZIP 自动归档，每条记录都能查到原件
6. **机票按附件拆分** — 往返机票拆为独立记录，不从一封邮件合并

---

## 🔭 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 1** | 规则引擎 — 域名+关键词+正则，零 API Key | ✅ 完成 |
| **Phase 1.5** | Agent 引擎 — LLM 增强 + 出差聚合 + 自动降级 | ✅ 完成 |
| **Phase 2** | Web 应用 — OAuth 登录 + 可视化行程卡片 + 云同步 | 📋 规划中 |
| **Phase 3** | 团队版 — 多人协作 + 审批流 + 财务系统对接 | 💡 构思中 |

---

## ❓ 常见问题

**Q: 必须配置 LLM API Key 才能用吗？**  
不用。不配也能完整使用，走纯规则引擎。LLM 是锦上添花的增强选项。

**Q: 会修改我邮箱里的邮件吗？**  
绝对不会。只有 IMAP 只读权限，只读取不修改、不删除、不发送。

**Q: 支持哪些邮箱？**  
QQ / 163 / 126 / Gmail / Outlook，理论上所有标准 IMAP 邮箱都支持。

**Q: 数据存在哪里？**  
全部在你本地 `output/` 目录，不上传任何服务器。

更多问题见 [FAQ](docs/faq.md)

---

## 🤝 贡献

欢迎各种形式的贡献！

- 🐛 [报告 Bug](../../issues/new?template=bug_report.md)
- 💡 [提功能建议](../../issues/new?template=feature_request.md)
- 📝 改进文档
- 🔧 提交代码修复或新功能
- 🌐 新增平台解析器

详细指南见 [贡献指南](CONTRIBUTING.md)

---

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

---

<div align="center">

如果这个工具帮你节省了时间，点个 ⭐ Star 支持一下吧！

Made with ❤️ by [HAO-Miracle](https://github.com/Hao-Miracle)

</div>
