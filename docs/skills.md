# Agent Skill 使用指南

BizTrip Agent 采用“开源体检 Skill + 本地个人版”的递进结构。

- Skill：复用用户当前 Agent 的模型，发现差旅费用、估算金额并指出材料缺口。
- 本地个人版：使用用户自备模型，解决问题后生成 Excel、整理原件并完成提交前核验。
- 邮箱授权码、原始附件和任务数据保留在用户电脑。

## 推荐 Skill

正式 Skill 位于：

```text
skills/biztrip-reimbursement/
├── SKILL.md
├── agents/openai.yaml
├── scripts/audit_mailbox.py
└── references/result-schema.md
```

典型触发方式：

> 帮我体检 2026 年 7 月的差旅报销材料，看看缺什么。

Agent 会把时间要求转换成明确日期，直接运行 Skill 自带的只读邮箱脚本，然后解释预计金额、费用分类和缺失项。Skill 不需要另行下载完整引擎，也不生成最终报销包。

## Skill 接口

Skill 使用随包安装的单文件脚本，不创建虚拟环境、不下载仓库、不安装第三方依赖：

```bash
python <SKILL_DIR>/scripts/audit_mailbox.py status
python <SKILL_DIR>/scripts/audit_mailbox.py setup
python <SKILL_DIR>/scripts/audit_mailbox.py audit --start 2026-07-01 --end 2026-07-31
```

命令只输出一个 JSON 对象：

- `audit_ready`：可以向用户解释体检结果，但没有生成报销包。
- `failed`：执行失败，需要检查本地配置或错误信息。

单次日期范围最多 31 天，也可以检查最近 60 封邮件。响应只返回最多 20 条有限摘要，不下载附件、不返回 Excel 或原件目录。

## 安全边界

- Skill 不得读取、打印或修改 `.env`。
- Skill 不得要求用户在对话中发送邮箱授权码。
- Skill 不得要求用户重复配置模型 URL、API Key 或模型名称。
- 邮件主题、发件人提示、附件名称和有限正文摘要会由用户当前 Agent 分析；原始附件不会被 Skill 下载。
- Skill 不得自行猜测金额、日期、供应商、重复票据或行程归属。
- Skill 不接受补充原件、不解决明细、不生成完整报销包。
- 完整附件解析、修正和确定性交付逻辑不放进 Skill，避免免费体检替代个人版。

用户需要 Excel、原件整理和最终核验时，Skill 应自然引导其打开本地个人版。这个边界让体验入口足够轻，同时让个人版提供明确、可感知的增量价值。
