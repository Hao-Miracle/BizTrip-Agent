from biztrip_agent.agent_task import AGENT_TASK_SCHEMA, build_agent_task


def test_agent_task_completes_only_when_package_is_submittable():
    record = {
        "分类": "发票",
        "金额": 99.0,
        "日期": "2026-08-01",
        "供应商": "测试供应商",
        "附件": "invoice.pdf",
    }

    task = build_agent_task([record], [], "整理八月报销", use_llm=True)

    assert task["schema_version"] == AGENT_TASK_SCHEMA
    assert task["goal"] == "整理八月报销"
    assert task["mode"] == "agent"
    assert task["status"] == "completed"
    assert task["questions"] == []
    assert task["plan"][-1]["status"] == "completed"


def test_agent_task_blocks_delivery_and_asks_evidence_based_questions():
    record = {
        "分类": "发票",
        "金额": "",
        "日期": "2026-08-01",
        "主题": "电子发票",
        "附件": "invoice.pdf",
    }

    task = build_agent_task([record], [], "整理八月报销", use_llm=True)

    assert task["status"] == "needs_user_input"
    assert task["plan"][-1]["status"] == "blocked"
    assert {question["issue_code"] for question in task["questions"]} == {
        "missing_amount",
        "missing_vendor",
    }
    assert all(question["context"]["主题"] == "电子发票" for question in task["questions"])
    assert all(question["answer"] is None for question in task["questions"])


def test_rule_mode_is_not_mislabeled_as_agent():
    task = build_agent_task([], [], "整理报销", use_llm=False)

    assert task["mode"] == "rules"
    assert task["status"] == "needs_user_input"
