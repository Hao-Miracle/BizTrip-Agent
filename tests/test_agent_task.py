from biztrip_agent.agent_task import (
    AGENT_TASK_SCHEMA,
    build_agent_task,
    recover_record_fields,
    run_recovery_loop,
)


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
    assert set(task["questions"][0]["issue_codes"]) == {
        "missing_amount",
        "missing_vendor",
    }
    assert all(question["context"]["主题"] == "电子发票" for question in task["questions"])
    assert all(question["answer"] is None for question in task["questions"])


def test_rule_mode_is_not_mislabeled_as_agent():
    task = build_agent_task([], [], "整理报销", use_llm=False)

    assert task["mode"] == "rules"
    assert task["status"] == "needs_user_input"


def test_recovery_uses_existing_structured_evidence_without_guessing():
    records = [
        {
            "分类": "酒店",
            "金额": 500.0,
            "入住日期": "2026-08-02",
            "酒店名称": "测试酒店",
            "附件": "hotel.pdf",
        },
        {
            "分类": "发票",
            "金额": 88.0,
            "日期": "2026-08-03",
            "商家": "测试餐厅",
            "附件": "invoice.pdf",
        },
    ]

    actions = recover_record_fields(records)

    assert records[0]["日期"] == "2026-08-02"
    assert records[1]["供应商"] == "测试餐厅"
    assert len(actions) == 2
    assert all(action["source"] == "existing_evidence" for action in actions)


def test_recovery_records_attachment_backfill_and_reduces_open_issues():
    records = [
        {
            "分类": "发票",
            "金额": "",
            "日期": "2026-08-03",
            "供应商": "12306",
            "附件": "train.zip",
        }
    ]

    before = build_agent_task(records, [], "整理报销", use_llm=True)
    actions = recover_record_fields(
        records,
        attachment_recoverer=lambda items: items[0].update({"金额": 149.0}),
    )
    after = build_agent_task(
        records,
        [],
        "整理报销",
        use_llm=True,
        initial_validation={
            **before["evidence"],
            "issue_count": before["evidence"]["issue_count"],
        },
        recovery_actions=actions,
    )

    assert records[0]["金额"] == 149.0
    assert actions[0]["field"] == "金额"
    assert after["status"] == "completed"
    assert after["evidence"]["resolved_issue_count"] == 1
    assert after["decisions"][0]["action"] == "use_tool"


def test_recovery_plans_only_tools_required_by_open_issues():
    records = [
        {
            "分类": "发票",
            "金额": 88.0,
            "日期": "2026-08-03",
            "商家": "测试餐厅",
            "附件": "invoice.pdf",
        }
    ]
    attachment_calls = []

    _trips, _initial, actions = run_recovery_loop(
        records,
        [],
        attachment_recoverer=lambda items: attachment_calls.append(items),
    )

    assert records[0]["供应商"] == "测试餐厅"
    assert [action["tool"] for action in actions] == ["resolve_vendor"]
    assert attachment_calls == []


def test_recovery_stops_when_tools_find_no_evidence():
    records = [
        {
            "分类": "发票",
            "金额": "",
            "日期": "",
            "供应商": "测试供应商",
            "附件": "invoice.pdf",
        }
    ]
    calls = []

    _trips, _initial, actions = run_recovery_loop(
        records,
        [],
        attachment_recoverer=lambda items: calls.append(items),
        max_rounds=5,
    )

    assert len(calls) == 1
    assert {action["result"] for action in actions} == {"no_evidence"}
    assert {action["round"] for action in actions} == {1}


def test_questions_are_combined_per_record():
    task = build_agent_task(
        [{"分类": "发票", "主题": "电子发票"}],
        [],
        "整理报销",
        use_llm=True,
    )

    assert len(task["questions"]) == 1
    assert set(task["questions"][0]["issue_codes"]) == {
        "missing_amount",
        "missing_date",
        "missing_vendor",
        "missing_attachment",
    }


def test_verified_llm_evidence_is_used_after_rule_tools_fail():
    records = [
        {
            "分类": "发票",
            "金额": "",
            "日期": "2026-08-03",
            "供应商": "测试供应商",
            "附件": "invoice.pdf",
        }
    ]

    _trips, _initial, actions = run_recovery_loop(
        records,
        [],
        attachment_recoverer=lambda _items: None,
        evidence_resolver=lambda _record, _codes: [
            {
                "field": "金额",
                "value": 88.0,
                "confidence": 0.98,
                "quote": "价税合计 88.00 元",
            }
        ],
    )

    assert records[0]["金额"] == 88.0
    assert actions[-1]["tool"] == "llm_evidence_analysis"
    assert actions[-1]["source"] == "verified_quote"


def test_unassigned_trip_question_contains_existing_trip_choices():
    assigned = {
        "记录ID": "R0001",
        "分类": "火车票",
        "金额": 100.0,
        "日期": "2026-08-01",
        "平台": "12306",
        "附件": "a.pdf",
    }
    unassigned = {
        "记录ID": "R0002",
        "分类": "火车票",
        "金额": 80.0,
        "日期": "2026-08-01",
        "平台": "12306",
        "附件": "b.pdf",
    }
    trips = [
        {
            "trip_id": 3,
            "summary": "上海出差",
            "records": [assigned],
            "total": 100.0,
        }
    ]

    task = build_agent_task([assigned, unassigned], trips, "整理报销", use_llm=True)

    question = next(item for item in task["questions"] if item["record_index"] == 2)
    assert question["options"] == [
        {
            "issue_code": "unassigned_trip",
            "value": "3",
            "label": "上海出差",
        }
    ]
