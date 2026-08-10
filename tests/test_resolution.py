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
