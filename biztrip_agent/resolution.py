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
    "unassigned_trip": "行程归属",
    "possible_duplicate": "duplicate_action",
    "identifier_conflict": "duplicate_action",
    "missing_attachment": "附件",
    "unreadable_attachment": "附件",
}


def resolve_results(json_path, answers, output_dir=None):
    """Apply allowed answers, revalidate, and write a new package without overwriting."""
    json_path = Path(json_path)
    payload = load_results_json(json_path)
    records = deepcopy(payload["records"])
    for index, record in enumerate(records, 1):
        record.setdefault("记录ID", f"R{index:04d}")
    questions = payload.get("agent_task", {}).get("questions", [])
    _mark_pending_trip_choices(records, questions)
    actions = apply_answers(records, questions, answers)
    if not actions:
        raise ValueError("没有填写可用于解决当前问题的信息。")

    from phase2.agent_report import _generate_excel
    from phase2.llm_aggregate import aggregate_trips, apply_manual_trip_assignments

    target_dir = Path(output_dir) if output_dir else json_path.parent
    trips = _restore_trips(payload.get("trips", []), records)
    if not trips:
        trips = aggregate_trips(records, use_llm=False)
    else:
        trips = apply_manual_trip_assignments(trips, records)
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
        attachment_dir=json_path.parent / "附件",
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

    review_path = generate_review_html(
        records,
        trips,
        target_dir,
        scan_label,
        excel_path=xlsx_path,
        attachment_dir=json_path.parent / "附件",
    )
    results_path = write_results_json(
        records,
        trips,
        target_dir,
        scan_label,
        xlsx_path=xlsx_path,
        review_path=review_path,
        agent_task=agent_task,
        attachment_dir=json_path.parent / "附件",
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
    exclusions = []
    for key, raw_value in answers.items():
        if key not in allowed:
            continue
        value = _normalize_answer(key[1], raw_value)
        if value in (None, ""):
            continue
        index, issue_code = key
        if allowed[key] == "duplicate_action":
            if value != "exclude":
                continue
            exclusions.append(index)
            actions.append(_confirmation_action(index, issue_code, "记录", "已排除"))
            continue
        target = _target_field(records[index - 1], allowed[key])
        records[index - 1][target] = value
        if issue_code == "unassigned_trip":
            records[index - 1]["待确认行程"] = False
        actions.append(_confirmation_action(index, issue_code, target, value))
    for index in sorted(set(exclusions), reverse=True):
        records.pop(index - 1)
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
    if issue_code == "unassigned_trip":
        if not value.isdigit() or int(value) < 1:
            raise ValueError("请选择有效的行程。")
        return int(value)
    if issue_code in {"possible_duplicate", "identifier_conflict"}:
        return value if value == "exclude" else None
    if issue_code in {"missing_attachment", "unreadable_attachment"}:
        path = Path(value)
        if path.name != value or path.suffix.lower() not in {".pdf", ".zip", ".jpg", ".jpeg", ".png", ".heic"}:
            raise ValueError("原件文件格式无效。")
        return value
    return None


def _target_field(record, field):
    if field != "供应商":
        return field
    return "供应商" if record.get("分类") in {"发票", "酒店"} else "平台"


def _mark_pending_trip_choices(records, questions):
    for question in questions:
        if "unassigned_trip" not in question.get("issue_codes", []):
            continue
        index = int(question.get("record_index", 0))
        if 1 <= index <= len(records):
            records[index - 1]["待确认行程"] = True


def _confirmation_action(index, issue_code, field, value):
    return {
        "action": "user_confirmation",
        "record_index": index,
        "issue_code": issue_code,
        "field": field,
        "result": "confirmed",
        "value": value,
        "reason": "用户明确确认",
        "source": "user",
        "confirmed_at": datetime.now().isoformat(timespec="seconds"),
    }


def _restore_trips(saved_trips, records):
    by_record_id = {record.get("记录ID"): record for record in records if record.get("记录ID")}
    if not by_record_id:
        return []
    restored = []
    matched = 0
    for saved in saved_trips:
        trip_records = []
        for old_record in saved.get("records", []):
            record = by_record_id.get(old_record.get("记录ID"))
            if record is not None:
                trip_records.append(record)
                matched += 1
        restored.append(
            {
                **{key: value for key, value in saved.items() if key != "records"},
                "records": trip_records,
                "total": sum(record.get("金额", 0) or 0 for record in trip_records),
            }
        )
    return restored if matched else []
