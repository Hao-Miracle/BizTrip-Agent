---
title: "操作日志"
tags: [元数据, 日志]
created: 2026-06-30
---

# 操作日志

## [2026-08-07] strategy | 建立开源竞品与护城河基线
- 搜索并核实 TaxHacker、KDE Itinerary、Receipt Wrangler、AI Finance Office 和 Spliit 的能力边界
- 确认 IMAP 邮箱归集、票据提取和费用导出已经有成熟开源实现，不能单独构成护城河
- 将产品定位收紧为：中国商务差旅的订单与凭证配对、完整性验收和可直接提交的报销包
- 确定下一项 P0：结果验收层；随后是订单与凭证配对、用户修正闭环
- 明确暂不优先开发通用记账、定时扫描、企业审批流和 AI 聊天窗口

## [2026-06-30] setup | 初始化 BizTrip Agent 知识库
- 在 `biztrip-agent/` 下创建完整知识库结构
- AGENTS.md：配置 AI 协作知识库维护规则
- raw/：入库项目计划书和需求探索过程记录
- wiki/entities/product.md：产品定义页
- wiki/entities/competitors.md：竞品分析页
- wiki/concepts/architecture.md：技术架构页
- wiki/concepts/features.md：功能范围页
- wiki/concepts/decisions.md：决策记录页
- wiki/index.md：内容索引
- wiki/log.md：操作日志

**当前阶段**：Phase 1 工作流验证（待开始）

## [2026-06-30] design | 基于 Anthropic Architecture 优化工作流
- 重读 Anthropic《构建有效 AI Agent》
- 应用决策流程图分析 BizTrip Agent 的工作流模式选择
- 设计三层架构：Level 1 提示链+路由（MVP）/ Level 2 并行化 / Level 3 评估器-优化器
- 设计路由分类器和专用提取 prompt 模板
- 设计出差聚合编排逻辑
- 新建 wiki/concepts/workflow.md

## [2026-06-30] decision | 出差和旅行使用同一套引擎
- 出差和旅行底层逻辑一致，区别只在有无发票
- 产品改为双模式：出差模式（行程卡+报销表）和旅行模式（行程卡+日程表）
- 已更新 wiki/entities/product.md 和 wiki/concepts/decisions.md

## [2026-06-30] fix | Phase 1 数据准确性修复
- **滴滴金额修复**：金额提取模式优先级调整，`合[计]...元` 优先于 `¥` 格式，防止误匹配发票税额
- **机票拆分修复**：增加按 PDF 附件拆分机票记录的逻辑，从文件名解析日期/路线/金额
- **扫描范围调整**：从 60 封扩大至 200 封，覆盖去程机票
- **清理调试脚本**：删除 phase1/ 下 8 个一次性 debug 脚本，保持目录整洁
- **输出目录修正**：generate_report.py OUTPUT_DIR 改为指向项目 output/（沙箱限制时退到 /tmp/）
- **知识库更新**：AGENTS.md 补充完整项目结构，decisions.md 记录两项架构决策

## [2026-07-04] spec | 创建 Phase 1 规格说明
- 新建 wiki/concepts/phase1-spec.md，完整描述 Phase 1 四个模块的规格
- 整合已有需求文档、决策记录、工作流设计中的散落信息
- 覆盖内容：模块输入/输出定义、分类规则约定、各平台提取字段规范、金额优先级、PDF 拆分逻辑、Excel 输出规格、验收标准
- 更新 wiki/index.md 索引

## [2026-07-04] agent | Phase 1.5 Agent 引擎开发
- 新建 phase2/ 目录，4 个模块：
  - `llm_classify.py`: LLM 路由分类（7 品类判断 + 置信度），低置信度自动降级正则
  - `llm_extract.py`: LLM 专用提取（5 品类专用 prompt），质量不足自动降级正则
  - `llm_aggregate.py`: LLM 出差聚合（时间+目的地归并），LLM 不可用时规则兜底
  - `agent_report.py`: Agent 模式主入口，自动检测 API Key，无 Key 时降级纯规则引擎
- 新增 `.env.example`: 配置模板（邮箱 + LLM 可选）
- 新增 Skill: `.trae/skills/agent-report/`
- 更新 README: 新增 Agent 模式说明、Phase 1.5 路线图
- 设计原则：开源友好，用户用自己的 API Key，不配 Key 也能完整使用

## [2026-07-04] config | 多模型支持 + Agent 配置文档
- 环境变量统一：`LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`，向下兼容旧 `DEEPSEEK_*` 变量
- 支持服务商：DeepSeek / 通义千问 / GLM / Kimi / SiliconFlow / 火山引擎 / Ollama 本地模型
- 新建 wiki/concepts/agent-config.md：完整多服务商接入文档
- .env.example 新增 7 个服务商配置示例
- README 新增 Agent 配置说明章节
- .gitignore 新增 output/ 排除
- 更新 wiki/index.md 索引

## [2026-07-04] skills | 创建 TRAE 自定义 Skills
- 新建 `.trae/skills/` 下 4 个 Skill，每个 Skill 对应一个 Phase 1 模块
  - `fetch-emails`: IMAP 连接与邮件获取
  - `classify-emails`: 规则分类引擎
  - `extract-emails`: 结构化提取（平台解析器 + PDF 处理 + 金额优先级）
  - `generate-report`: 全链路扫描 + Excel 生成 + 附件归档
- 每个 SKILL.md 包含：用途、用法、规则说明、注意事项
- 更新 wiki/index.md 索引

## [2026-07-04] tasks | 创建 Phase 1 任务拆解
- 新建 wiki/concepts/phase1-tasks.md
- 33 个任务全部标记为已完成的复盘文档
- 按：基础设施 → 模块开发 → 数据准确性 → 输出 → 验证修复 五组归类
- 更新 wiki/index.md 索引
