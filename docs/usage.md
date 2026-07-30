# 使用指南

本文档介绍 BizTrip Agent 的详细使用方法。

---

## 快速开始

### 本地 Web 工作台

```bash
biztrip web
```

`web` 会启动只绑定本机的页面。账号只需要配置一次；之后填写本次报销期间并点击“开始生成”，系统会按邮箱地址自动选择 IMAP 服务器并生成报销包。

页面顶部只显示一个准备状态，例如“可以开始生成报销包”或“需要先保存邮箱账号”。Python、依赖、`.env` 和 LLM 状态会折叠在“诊断信息”里，排查问题时再展开。诊断信息只显示是否已配置，不会展示邮箱授权码或 API Key。页面里的“修复配置文件”按钮不会覆盖已有 `.env`。

如果 `.env` 已存在但还没填写内容，可以直接在页面的“账号”区域填写邮箱账号和邮箱授权码。系统会按邮箱地址自动选择 IMAP 服务器；高级配置默认折叠，授权码和 API Key 保存后不会回显。

第一次使用时，页面会显示“第一次使用”指引：
1. 打开邮箱设置，开启 IMAP/SMTP 服务
2. 生成邮箱授权码或应用专用密码，不要使用登录密码
3. 回到页面填写邮箱账号和授权码，点击“保存账号”

保存后普通使用不需要再配置邮箱。

测试首次使用流程时，可以用临时配置启动，不影响真实 `.env`：

```bash
BIZTRIP_ENV_PATH=/tmp/biztrip-first-run.env biztrip web --port 8766
```

如果不想自动打开浏览器：

```bash
biztrip web --no-open
```

默认会输出到 `output/` 并生成审阅页面。报销期间决定结果边界；需要调整扫描邮件数量、输出目录或规则模式时，展开“高级扫描选项”。普通使用不需要 LLM；想增强复杂邮件识别时，展开“LLM 增强配置”填写接口地址、API Key 和模型名称。配置后不需要进入对话窗口，点击“开始生成”时系统会自动调用 LLM 辅助分类、提取和行程聚合。

点击“开始生成”后会进入后台任务模式，页面会显示排队、运行、完成或失败状态。扫描成功后会列出 Excel 和审阅页路径；扫描失败时会优先显示可读原因，例如授权码错误、IMAP 未开启、网络失败或输出目录不可写。

### 引导模式

```bash
biztrip wizard
```

`wizard` 会用问答方式引导你生成 Demo、重新生成报表，或检查本地环境。它不会读取邮箱，也不会修改邮箱配置。

### 先跑 Demo（不需要邮箱）

```bash
biztrip demo
```

运行后会用虚构差旅数据生成示例报表：

```
output/差旅汇总_demo_YYYYMMDD_HHMMSS.xlsx
```

这一步不读取 `.env`，也不会连接邮箱。

如果想同时生成本地审阅页面：

```bash
biztrip demo --review
```

审阅页面会输出到：

```
output/review_YYYYMMDD_HHMMSS.html
```

### 检查本地环境

```bash
biztrip check
```

检查 Python 版本、必需依赖，以及 `.env` 是否存在。

### 初始化配置

```bash
biztrip init
```

该命令会从 `.env.example` 创建 `.env`。编辑 `.env` 后再扫描真实邮箱。

### 规则模式（零 API Key）

```bash
python3 phase1/generate_report.py
```

运行后按提示操作：

1. 输入开始日期（`YYYY-MM-DD`），或直接回车跳过
2. 输入结束日期，或直接回车扫描最近 60 封邮件
3. 等待扫描完成，结果会保存在 `output/` 目录

### Agent 模式（LLM 增强）

```bash
biztrip scan
```

Agent 模式在规则模式基础上增加：
- 🧠 更智能的邮件分类
- 📝 更精准的字段提取
- 🌍 自动出差聚合（按时间+目的地归并）

> 未配置 `LLM_API_KEY` 时自动降级为规则模式，零成本可用。

旧入口仍可用：

```bash
python3 phase2/agent_report.py
```

---

## 输出文件说明

运行后在 `output/` 目录生成：

```
output/
├── 差旅汇总_YYYYMMDD_HHMMSS.xlsx    ← 三 Sheet Excel 报表
├── records_YYYYMMDD_HHMMSS.json      ← 系统留档
└── 附件/                        ← 原始 PDF/ZIP 原件归档
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
| **费用明细** | 所有记录，按日期排序，最高金额红色高亮，标注提取方法 |
| **按供应商** | 各平台消费排名，隔行配色 |

`records_YYYYMMDD_HHMMSS.json` 是系统留档，普通使用只需要打开 Excel 和审阅页。后续复查问题或重新生成报表时，可以优先复用这个文件，避免反复扫描邮箱。文件名带生成时间，同一天重复扫描不会覆盖旧结果。

### 从系统留档重新生成

```bash
biztrip rebuild output/records_YYYYMMDD_HHMMSS.json
biztrip rebuild output/records_YYYYMMDD_HHMMSS.json --review
biztrip rebuild output/records_YYYYMMDD_HHMMSS.json --output-dir output/rebuilt
```

`rebuild` 不会连接邮箱，只读取已保存的 JSON 结果，重新生成 Excel 和可选的 HTML 审阅页。

---

## 支持的平台

### ✈️ 机票
- 去哪儿、携程、飞猪、各航司官网邮件
- 支持 PDF 附件拆分，往返机票拆为独立记录

### 🚄 火车票
- 12306、智行
- 提取车次、座位、出发/到达站、金额

### 🏨 酒店
- 华住、Booking、携程、美团
- 提取入住/离店日期、房型、金额

### 🚕 网约车
- 滴滴、高德（曹操/T3/及时/喜行等）
- 提取上下车时间、路线、金额

### 🧾 发票
- 智慧发票(cresvtv.cn)、票根(txffp.com)
- 提取发票号码、金额、开票日期

### 🎫 门票
- 大麦
- 提取演出/活动名称、日期、金额

---

## 金额提取优先级

为保证数据准确，金额提取遵循以下优先级：

1. **PDF 文件名** — 最可靠，航司/平台直接命名
2. **价税合计** — PDF 文本中的"价税合计"字段
3. **合计...元** — 邮件正文中的"合计 XX 元"
4. **¥ 符号** — 兜底，取第一个出现的金额

> ⚠️ 绝不对税额做提取，只取实际支付金额。

---

## 命令行命令

### biztrip

```bash
biztrip demo    # 生成示例 Excel，不连接邮箱
biztrip check   # 检查环境和配置
biztrip init    # 创建 .env
biztrip wizard  # 引导式本地流程
biztrip web     # 本地 Web 工作台
biztrip scan    # 运行交互式邮箱扫描
```

`biztrip scan` 默认会询问日期范围，直接回车则扫描最近 60 封邮件。也可以传入参数，跳过交互：

```bash
biztrip scan --start 2026-07-01 --end 2026-07-29
biztrip scan --count 100
biztrip scan --no-llm
biztrip scan --output-dir output/monthly
biztrip scan --review
```

参数说明：

| 参数 | 作用 |
|------|------|
| `--start YYYY-MM-DD` | 按开始日期过滤邮件 |
| `--end YYYY-MM-DD` | 按结束日期过滤邮件 |
| `--count N` | 未指定日期时扫描最近 N 封邮件 |
| `--no-llm` | 强制规则模式，不调用 LLM |
| `--output-dir PATH` | 指定报表和附件输出目录 |
| `--review` | 额外生成本地 HTML 审阅页面 |

审阅页面会列出总金额、行程汇总、费用明细，并把缺金额、缺日期、无附件的记录标成需检查。

### 旧脚本入口

```bash
python3 phase1/generate_report.py
python3 phase2/agent_report.py
```

## 运行测试

```bash
pip install -e ".[test]"
pytest
```

测试使用虚构样本，覆盖分类、字段提取、出差聚合、Demo Excel 和 HTML 审阅页，不会连接真实邮箱。

---

## 隐私与安全

- 🔒 **本地处理** — 所有邮件数据仅在你本地机器处理
- 📖 **只读权限** — 只读取邮件，不修改、不删除、不发送
- 🔑 **授权码** — 使用邮箱授权码而非登录密码，可随时撤销
- 📦 **附件归档** — 原始 PDF/ZIP 保存在本地，方便溯源

---

## 卸载

直接删除项目目录即可，所有数据都在本地，不留任何残留。

```bash
# 注意：output/ 目录包含你的邮件附件，删除前请备份
rm -rf BizTrip-Agent
```
