from biztrip_agent.agent_task import build_agent_task
from biztrip_agent.resolution import apply_answers, resolve_results
from biztrip_agent.results import load_results_json, write_results_json


def test_apply_answers_changes_only_current_open_questions():
    records = [
        {"分类": "发票", "金额": "", "日期": "", "供应商": "", "附件": "invoice.pdf"},
        {"分类": "发票", "金额": 20.0, "日期": "2026-08-01", "供应商": "商店", "附件": "ok.pdf"},
    ]
    task = build_agent_task(records, [], "整理报销", use_llm=True)

    actions = apply_answers(
        records,
        task["questions"],
        {
            (1, "missing_amount"): "88.50",
            (1, "missing_date"): "2026-08-02",
            (1, "missing_vendor"): "测试餐厅",
            (2, "missing_amount"): "999",
        },
    )

    assert records[0]["金额"] == 88.5
    assert records[0]["日期"] == "2026-08-02"
    assert records[0]["供应商"] == "测试餐厅"
    assert records[1]["金额"] == 20.0
    assert len(actions) == 3
    assert all(action["source"] == "user" for action in actions)


def test_resolve_results_revalidates_and_writes_new_package(tmp_path):
    records = [
        {"分类": "发票", "金额": "", "日期": "2026-08-02", "供应商": "测试餐厅", "附件": "invoice.pdf"}
    ]
    task = build_agent_task(records, [], "整理报销", use_llm=True)
    source = write_results_json(records, [], tmp_path, "八月报销", agent_task=task)

    result = resolve_results(source, {(1, "missing_amount"): "88.50"})

    payload = load_results_json(result["results_path"])
    assert result["results_path"] != source
    assert payload["records"][0]["金额"] == 88.5
    assert payload["summary"]["can_submit"] is True
    assert payload["agent_task"]["status"] == "completed"
    assert any(action["action"] == "user_confirmation" for action in payload["agent_task"]["decisions"])


def test_user_can_exclude_one_confirmed_duplicate(tmp_path):
    records = [
        {"记录ID": "R0001", "分类": "发票", "订单号": "A1", "金额": 20.0, "日期": "2026-08-01", "供应商": "商店", "附件": "a.pdf"},
        {"记录ID": "R0002", "分类": "发票", "订单号": "A1", "金额": 20.0, "日期": "2026-08-01", "供应商": "商店", "附件": "b.pdf"},
    ]
    task = build_agent_task(records, [], "整理报销", use_llm=True)
    source = write_results_json(records, [], tmp_path, "八月报销", agent_task=task)

    result = resolve_results(source, {(2, "possible_duplicate"): "exclude"})

    payload = load_results_json(result["results_path"])
    assert len(payload["records"]) == 1
    assert payload["summary"]["can_submit"] is True
    assert any(
        action.get("issue_code") == "possible_duplicate" and action.get("value") == "已排除"
        for action in payload["agent_task"]["decisions"]
    )


def test_user_trip_choice_keeps_original_trip_identity(tmp_path):
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
            "trip_id": 7,
            "destination": "上海",
            "start_date": "2026-08-01",
            "end_date": "2026-08-01",
            "summary": "上海出差",
            "records": [assigned],
            "total": 100.0,
            "method": "LLM",
        }
    ]
    task = build_agent_task([assigned, unassigned], trips, "整理报销", use_llm=True)
    source = write_results_json([assigned, unassigned], trips, tmp_path, "八月报销", agent_task=task)

    result = resolve_results(source, {(2, "unassigned_trip"): "7"})

    payload = load_results_json(result["results_path"])
    assert payload["summary"]["can_submit"] is True
    assert payload["trips"][0]["trip_id"] == 7
    assert {record["记录ID"] for record in payload["trips"][0]["records"]} == {"R0001", "R0002"}
