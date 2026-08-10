# Agent Skill 使用指南

BizTrip Agent 采用“开源薄 Skill + 本地确定性引擎”的结构。

- Skill：理解用户目标、调用引擎、追问待确认信息、解释结果。
- 本地引擎：读取邮箱、解析原件、核验数据、计算金额、生成报销包。
- 邮箱授权码、API Key、原始附件和报销包保留在用户电脑；云端模型会接收必要的邮件和票据文本。

## 推荐 Skill

正式 Skill 位于：

```text
skills/biztrip-reimbursement/
├── SKILL.md
├── agents/openai.yaml
└── references/result-schema.md
```

典型触发方式：

> 帮我整理 2026 年 7 月的差旅报销。

Agent 会把时间要求转换成明确日期，调用本地引擎，并根据核验结果继续询问。只有本地引擎返回 `completed` 后，Agent 才会交付报销包。

## 引擎接口

Skill 通过三个结构化命令与本地引擎协作：

```bash
biztrip agent start --start 2026-07-01 --end 2026-07-31
biztrip agent status
biztrip agent answer --task TASK_PATH --answers-file ANSWERS.json
```

每个命令只输出一个 JSON 对象，状态固定为：

- `completed`：核验通过，可以交付报销包。
- `needs_user_input`：需要用户确认指定信息。
- `failed`：执行失败，需要检查本地配置或错误信息。

## 安全边界

- Skill 不得读取、打印或修改 `.env`。
- Skill 不得要求用户在对话中发送邮箱授权码或 API Key。
- Skill 不得自行猜测金额、日期、供应商、重复票据或行程归属。
- 原件缺失时通过本地 Web 页面补充，不上传到外部 Agent 服务。
- 核心识别和核验逻辑不放进 Skill，避免不同 Agent 执行环境造成结果漂移。

仓库只推荐这一份薄 Skill。邮件读取、分类、提取和报表生成属于本地引擎内部能力，不再拆成多个会暴露实现步骤的用户 Skill。
