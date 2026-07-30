# 安装指南

本文档介绍如何安装和配置 BizTrip Agent。

---

## 前置要求

| 要求 | 说明 |
|------|------|
| **Python** | ≥ 3.8 |
| **邮箱** | 已开启 IMAP 服务，并获取授权码/应用专用密码 |
| **LLM API Key（可选）** | 如需 AI 增强功能，准备兼容 OpenAI 协议的 API Key |

如果不确定电脑有没有 Python：

```bash
python3 --version
```

如果提示找不到 `python3`，或版本低于 `3.8`，先安装 Python 3.8+。macOS 用户可以从 [python.org](https://www.python.org/downloads/) 安装，或使用 Homebrew：

```bash
brew install python
```

---

## 支持的邮箱服务商

| 邮箱 | IMAP 服务器 | 端口 | 如何获取授权码 |
|------|-----------|------|--------------|
| QQ 邮箱 | `imap.qq.com` | 993 | 设置 → 账户 → POP3/IMAP/SMTP 服务 |
| 163 邮箱 | `imap.163.com` | 993 | 设置 → POP3/SMTP/IMAP → 开启并获取 |
| 126 邮箱 | `imap.126.com` | 993 | 同上 |
| Gmail | `imap.gmail.com` | 993 | 开启两步验证 → 生成应用专用密码 |
| Outlook/Hotmail | `outlook.office365.com` | 993 | 账户安全 → 应用密码 |

> 代码会根据 `@域名` 自动推断 IMAP 服务器，也可在 `.env` 中手动指定。

---

## 安装步骤

### 一条命令安装并启动

```bash
git clone https://github.com/Hao-Miracle/BizTrip-Agent.git && cd BizTrip-Agent && python3 -m venv .venv && .venv/bin/python -m pip install -e . && .venv/bin/biztrip web
```

这条命令会自动安装项目需要的 Python 依赖，包括 `python-dotenv`、`PyPDF2`、`openpyxl` 和本地 `biztrip` 命令。它不会自动安装 Python 本身，也不会替你开启邮箱 IMAP 或生成邮箱授权码。

### 下载 ZIP

直接从 [Releases](https://github.com/Hao-Miracle/BizTrip-Agent/releases) 下载最新版本的 ZIP 包，解压后进入目录。

---

## 手动安装依赖

通常不需要手动执行这些命令；一条命令安装会自动完成。需要排查安装问题时，可以手动运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/biztrip web
```

### LLM 增强依赖（可选）

普通报销扫描不需要安装 `openai`。只有启用 LLM 增强时才需要：

```bash
.venv/bin/python -m pip install -e ".[llm]"
```

---

## 首次配置

启动 Web 工作台：

```bash
biztrip web
```

第一次使用时，页面会显示配置指引：

1. 打开邮箱设置，开启 IMAP/SMTP 服务
2. 生成邮箱授权码或应用专用密码，不要使用登录密码
3. 回到页面填写邮箱账号和授权码，点击“保存账号”

系统会按邮箱地址自动选择 IMAP 服务器，并把配置保存在本机 `.env` 文件中。普通用户不需要手动编辑 `.env`。

### （可选）配置 LLM

普通报销扫描不需要 LLM。想启用增强识别时，在 Web 页面展开“高级配置”，填写 `LLM API Key` 即可。Base URL 和 Model 留空时，系统默认使用 DeepSeek：

| 字段 | 默认值 |
|------|--------|
| LLM Base URL | `https://api.deepseek.com/v1` |
| LLM Model | `deepseek-chat` |

高级用户也可以手动填写兼容 OpenAI 协议的其他服务商配置。更多服务商配置示例见 `.env.example`。

---

## 验证安装

运行以下命令验证是否正常：

```bash
biztrip web
```

如果浏览器打开本地工作台，并显示 Python、依赖和 `.env` 状态，说明安装成功。你可以先生成 Demo，再配置邮箱扫描真实邮件。

命令行验证也可以运行：

```bash
biztrip check
biztrip demo --review
```

---

## 常见安装问题

### Q: `ModuleNotFoundError: No module named 'xxx'`

A: 缺少依赖，重新安装：
```bash
pip install python-dotenv PyPDF2 openpyxl
```

### Q: 连接邮箱失败

A: 检查以下几点：
1. 邮箱是否开启了 IMAP 服务
2. 密码是否为**授权码**（不是登录密码）
3. 网络是否能访问 IMAP 服务器（企业网络可能有限制）

QQ 邮箱如果提示 `Login fail. Account is abnormal, service is not open, password is incorrect, login frequency limited...`，通常需要重新确认 IMAP/SMTP 已开启，并重新生成授权码；连续失败后可能会被临时限频，等待几分钟再试。

### Q: Python 版本不够

A: 升级 Python 到 3.8 或更高版本。推荐使用 [pyenv](https://github.com/pyenv/pyenv) 管理 Python 版本。

---

## 下一步

- 阅读 [使用指南](usage.md) 了解详细功能
- 查看 [常见问题](faq.md) 获取更多帮助
- 加入 [Discussions](../../discussions) 交流

## 发布检查清单

发布新版本前建议确认：

1. 更新 `pyproject.toml` 版本号
2. 更新 `CHANGELOG.md`
3. 运行 `pytest`
4. 运行 `biztrip web --no-open` 并确认本地页面可打开
5. 在 GitHub 创建 Release，并附上安装命令和主要变更
