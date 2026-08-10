<div align="center">

# BizTrip Agent

**把散落在邮箱里的机票、酒店、火车票、打车和发票，整理成经过核验的差旅报销包。**

你只需要告诉自己的 Agent：

> 帮我整理上个月的差旅报销。

BizTrip 会在本地收集凭证、识别费用、归并出差行程；发现缺失或冲突时先向你确认，全部通过后才交付 Excel 和报销原件。

<p>
  <a href="skills/biztrip-reimbursement/SKILL.md"><strong>安装开源 Skill</strong></a>
  ·
  <a href="#没有-agent也能使用">没有 Agent 也能使用</a>
  ·
  <a href="docs/usage.md">查看使用文档</a>
</p>

<p>
  <a href="https://github.com/Hao-Miracle/BizTrip-Agent/releases">
    <img src="https://img.shields.io/github/v/release/Hao-Miracle/BizTrip-Agent?style=flat-square" alt="release">
  </a>
  <img src="https://img.shields.io/badge/local--first-private-137333?style=flat-square" alt="local first">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="license">
  <a href="https://github.com/Hao-Miracle/BizTrip-Agent/stargazers">
    <img src="https://img.shields.io/github/stars/Hao-Miracle/BizTrip-Agent?style=flat-square&color=orange" alt="stars">
  </a>
</p>

</div>

---

## 从一句话开始

BizTrip 的首选入口是开源薄 Skill：[`biztrip-reimbursement`](skills/biztrip-reimbursement/SKILL.md)。它把 BizTrip 接入你正在使用的 Agent，而不是要求你学习新的报销软件。

把下面的地址交给支持 Skills 的 Agent，并让它安装：

```text
https://github.com/Hao-Miracle/BizTrip-Agent/tree/main/skills/biztrip-reimbursement
```

安装后直接提出任务：

```text
帮我整理 2026 年 7 月的差旅报销。
```

Skill 会：

1. 理解你要处理的时间范围。
2. 检测电脑上是否已有 BizTrip 本地引擎。
3. 未安装时先说明用途，获得同意后再安装免费开源引擎。
4. 引擎完成扫描、提取、行程归并和提交前核验。
5. 遇到缺失、重复或冲突时，只询问必须由你确认的问题。
6. 核验通过后交付报销包位置和总金额。

Skill 不读取或展示邮箱授权码、API Key，也不会把核心识别逻辑交给不同 Agent 随意执行。详细边界见 [Agent Skill 使用指南](docs/skills.md)。

---

## 为什么不是直接生成一张表

报销最危险的结果不是“没有结果”，而是得到一份看起来完整、实际有错误的表。

BizTrip 在交付前检查：

- 金额、日期和供应商是否完整有效。
- 每条费用是否有对应原件。
- 同一票据是否重复或存在编号冲突。
- 费用是否可靠归入某次出差。
- 行程日期和费用合计是否一致。

发现问题时，任务状态会停在“需要确认”；只有所有质量门槛通过后，系统才生成可提交的报销包。

---

## 你最终得到什么

```text
报销包_20260731_143022/
├── 差旅汇总_20260731_143022.xlsx
└── 原件/
    ├── 机票电子发票.pdf
    ├── 酒店发票.pdf
    └── 打车行程单.pdf
```

Excel 包含：

| 工作表 | 内容 |
|---|---|
| **报销总览** | 行程、总金额和费用分类 |
| **费用明细** | 日期、金额、供应商、路线、订单号和原件 |
| **按供应商** | 各平台的笔数、金额和占比 |

交付目录只包含本次报销真正引用的文件。运行状态、附件缓存和内部 JSON 留在系统目录，不要求普通用户处理。

---

## 本地处理，凭证不离开电脑

- 邮箱通过标准 IMAP 读取，不发送、不删除、不修改邮件。
- 邮箱授权码和可选 LLM API Key 只保存在用户本机。
- PDF、ZIP、Excel 和任务状态均保存在本地目录。
- Skill 不接收秘密配置，不替用户猜测财务数据。
- 不配置 LLM 也能使用规则引擎；配置后只增强复杂邮件识别。

支持 QQ、163、126、Gmail、Outlook 及其他标准 IMAP 邮箱。已覆盖 12306、去哪儿、携程、飞猪、航司邮件、酒店、滴滴、高德聚合打车、智慧发票、票根等常见来源。

---

## 没有 Agent 也能使用

Skill 是首选获客和使用入口，但本地引擎本身可以独立运行。

### Windows

当前提供未签名的 Windows 测试版，双击后打开本地 Web 工作台，不需要安装 Python 或 Git。它用于公开测试，不是未来唯一的产品形态。

查看 [Windows 测试版说明](docs/windows-one-click.md)。Windows SmartScreen 可能要求用户确认运行。

### macOS 和 Linux

正式 macOS 桌面安装包尚未发布。当前可以通过源码启动本地 Web 工作台：

```bash
git clone https://github.com/Hao-Miracle/BizTrip-Agent.git && cd BizTrip-Agent && python3 start.py
```

这条命令会创建隔离运行环境并安装依赖，不会替用户安装 Python、开启邮箱 IMAP 或生成邮箱授权码。完整说明见 [安装指南](docs/installation.md)。

后续会提供与 Windows 对等的正式桌面分发；在签名、公证和自动更新完成前，不把未经验证的 macOS 安装包包装成“一键正式版”。

---

## 第一次连接邮箱

本地页面会引导用户：

1. 在邮箱设置中开启 IMAP 服务。
2. 生成邮箱授权码或应用专用密码，不使用网页登录密码。
3. 在本地页面填写邮箱账号和授权码。
4. 选择本次报销的日期范围并开始生成。

系统会根据邮箱地址自动选择常见 IMAP 服务器。账号通常只需配置一次，页面不会回显授权码和 API Key。

---

## 可选 LLM 增强

基础版不要求 LLM API Key。规则引擎可以完成邮箱分类、字段提取、附件处理、核验和报销包生成。

复杂邮件需要增强识别时，可以在本地 Web 页面填写兼容 OpenAI 协议的接口地址、API Key 和模型名称。LLM 失败或证据不足时，系统会回退到规则与确定性校验，不会因为模型输出而绕过提交门槛。

支持用户自备的云端模型或本地模型，配置示例见 [.env.example](.env.example)。

---

## 免费边界与未来方向

当前仓库提供免费的开源 Skill 和单人本地引擎，目标是让个人用户低成本完成第一份可信的报销包。

未来的专业和团队能力将聚焦于持续服务，而不是把基础 Excel 导出重新收费：

- 企业报销制度和合规规则核验。
- 发票验真、异常检测和跨员工查重。
- 多员工、多邮箱、团队权限和审计记录。
- OA、ERP、财务系统及企业模板连接。
- 托管模型调用、自动更新、私有部署和技术支持。

这些能力仍在规划中，当前开源版本不宣称已经提供。

---

## 开发者入口

安装项目命令：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[llm,test]"
```

常用命令：

```bash
.venv/bin/biztrip web
.venv/bin/biztrip demo
.venv/bin/biztrip scan --start 2026-07-01 --end 2026-07-31
.venv/bin/biztrip agent status
.venv/bin/python -m pytest
```

Agent 通过稳定的 `start`、`status`、`answer` JSON 接口调用本地引擎，协议说明见 [Skill 结果结构](skills/biztrip-reimbursement/references/result-schema.md)。

### 项目结构

```text
BizTrip-Agent/
├── biztrip_agent/      本地任务、核验、交付、Web 和 Agent 接口
├── common/             邮件与通用解析能力
├── phase1/             规则解析流程
├── phase2/             可选 LLM 增强流程
├── skills/             开源薄 Skill 和兼容文件
├── tests/              本地与跨平台自动测试
└── docs/               安装、使用和常见问题
```

设计原则：

1. 数据准确是底线，模型不能绕过确定性核验。
2. 能删除的用户步骤先删除，再简化和自动化。
3. 核心引擎本地运行，Skill 只负责自然语言入口和任务编排。
4. 原始凭证可追溯，内部状态不污染用户交付物。
5. 新平台解析规则和缺陷修复欢迎通过 PR 贡献。

---

## 常见问题

**必须配置 LLM API Key 吗？**

不需要。LLM 是可选增强，不配置仍可使用规则模式。

**会修改邮箱里的邮件吗？**

不会。系统只读取邮件，不发送、不删除、不修改。

**为什么问题未解决时没有 Excel？**

因为一份错误但看似完整的报销表比没有结果更危险。需要确认的问题解决后才生成报销包。

**macOS 为什么暂时没有安装包？**

当前优先通过 Skill 和本地启动器验证产品闭环。正式 macOS 分发需要完成签名、公证和更新机制后再发布。

更多问题见 [FAQ](docs/faq.md)。

---

## 参与项目

- [报告问题](../../issues/new?template=bug_report.md)
- [提出产品建议](../../issues/new?template=feature_request.md)
- [查看更新日志](CHANGELOG.md)
- [阅读贡献指南](CONTRIBUTING.md)

如果 BizTrip 帮你减少了整理报销材料的时间，可以 Star 仓库，让更多需要它的人找到这个项目。

MIT License，详见 [LICENSE](LICENSE)。
