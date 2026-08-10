"""Apply explicit user answers and regenerate a verified reimbursement package."""

from copy import deepcopy
from datetime import datetime
from pathlib import Path

from biztrip_agent.agent_task import build_agent_task
from biztrip_agent.results import load_results_json, write_results_json


ANSWER_FIELDS = {
    "missing_amount": "金额",
    "missing_date": "日期",
    "missing_vendor": "供应商",
}


def resolve_results(json_path, answers, output_dir=None):
    """Apply allowed answers, revalidate, and write a new package without overwriting."""
    json_path = Path(json_path)
    payload = load_results_json(json_path)
    records = deepcopy(payload["records"])
    questions = payload.get("agent_task", {}).get("questions", [])
    actions = apply_answers(records, questions, answers)
    if not actions:
        raise ValueError("没有填写可用于解决当前问题的信息。")

    from phase2.agent_report import _generate_excel
    from phase2.llm_aggregate import aggregate_trips

    target_dir = Path(output_dir) if output_dir else json_path.parent
    trips = aggregate_trips(records, use_llm=False)
    previous_actions = [
        action
        for action in payload.get("agent_task", {}).get("decisions", [])
        if action.get("action") != "validate_submission"
    ]
    agent_task = build_agent_task(
        records,
        trips,
        goal=payload.get("agent_task", {}).get("goal") or f"整理并核验 {payload.get('scan_label', '')} 的差旅报销材料",
        use_llm=payload.get("agent_task", {}).get("mode") == "agent",
        initial_validation=payload.get("validation"),
        recovery_actions=[*previous_actions, *actions],
    )
    total = sum(record.get("金额", 0) or 0 for record in records)
    scan_label = payload.get("scan_label") or "用户确认"
    xlsx_path = _generate_excel(
        records,
        trips,
        total,
        scan_label,
        output_dir=str(target_dir),
        use_llm=agent_task["mode"] == "agent",
    )
    from biztrip_agent.review import generate_review_html

    review_path = generate_review_html(records, trips, target_dir, scan_label, excel_path=xlsx_path)
    results_path = write_results_json(
        records,
        trips,
        target_dir,
        scan_label,
        xlsx_path=xlsx_path,
        review_path=review_path,
        agent_task=agent_task,
    )
    return {
        "records": records,
        "trips": trips,
        "agent_task": agent_task,
        "xlsx_path": xlsx_path,
        "review_path": review_path,
        "results_path": results_path,
    }


def apply_answers(records, questions, answers):
    """Apply only answers corresponding to currently open, editable issues."""
    allowed = {}
    for question in questions:
        index = int(question.get("record_index", 0))
        for issue_code in question.get("issue_codes", []):
            field = ANSWER_FIELDS.get(issue_code)
            if field and 1 <= index <= len(records):
                allowed[(index, issue_code)] = field

    actions = []
    for key, raw_value in answers.items():
        if key not in allowed:
            continue
        value = _normalize_answer(key[1], raw_value)
        if value in (None, ""):
            continue
        index, issue_code = key
        target = _target_field(records[index - 1], allowed[key])
        records[index - 1][target] = value
        actions.append(
            {
                "action": "user_confirmation",
                "record_index": index,
                "issue_code": issue_code,
                "field": target,
                "result": "confirmed",
                "value": value,
                "reason": "用户明确确认",
                "source": "user",
                "confirmed_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
    return actions


def _normalize_answer(issue_code, value):
    value = str(value or "").strip()
    if not value:
        return None
    if issue_code == "missing_amount":
        try:
            amount = float(value)
        except ValueError as exc:
            raise ValueError("金额必须是大于 0 的数字。") from exc
        if amount <= 0:
            raise ValueError("金额必须是大于 0 的数字。")
        return round(amount, 2)
    if issue_code == "missing_date":
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("日期必须使用 YYYY-MM-DD 格式。") from exc
        return value
    if issue_code == "missing_vendor":
        if len(value) > 120:
            raise ValueError("供应商名称过长，请检查后重新填写。")
        return value
    return None


def _target_field(record, field):
    if field != "供应商":
        return field
    return "供应商" if record.get("分类") in {"发票", "酒店"} else "平台"
