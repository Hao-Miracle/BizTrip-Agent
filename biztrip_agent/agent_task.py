"""Build a traceable task state for one reimbursement goal."""

from datetime import datetime

from biztrip_agent.validation import validate_reimbursement


AGENT_TASK_SCHEMA = "biztrip.agent-task.v1"

ISSUE_PROMPTS = {
    "missing_amount": "这条凭证缺少金额，请确认正确金额或补充包含金额的原件。",
    "missing_date": "这条凭证缺少日期，请确认发生日期。",
    "missing_vendor": "这条凭证缺少供应商，请确认实际收款方。",
    "missing_attachment": "这条记录没有找到报销原件，请补充对应凭证。",
    "unassigned_trip": "这条费用无法可靠归入现有行程，请确认它属于哪次出差。",
    "identifier_conflict": "相同票据编号对应了不同信息，请确认哪条记录正确。",
    "possible_duplicate": "发现疑似重复凭证，请确认是否只保留一条。",
}


def build_agent_task(records, trips, goal, use_llm):
    """Describe the current goal, completed work and required next decisions."""
    validation = validate_reimbursement(records, trips)
    questions = _questions_from_validation(records, validation)
    ready = validation["can_submit"]

    return {
        "schema_version": AGENT_TASK_SCHEMA,
        "goal": goal,
        "mode": "agent" if use_llm else "rules",
        "status": "completed" if ready else "needs_user_input",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "plan": [
            _step("collect", "收集范围内的邮件和凭证", "completed"),
            _step("understand", "识别费用并整理行程", "completed"),
            _step("verify", "核验报销材料完整性", "completed"),
            _step("resolve", "解决缺失、冲突和重复问题", "completed" if ready else "waiting"),
            _step("deliver", "交付可提交的报销包", "completed" if ready else "blocked"),
        ],
        "evidence": {
            "record_count": len(records),
            "trip_count": len(trips),
            "complete_count": validation["complete_count"],
            "affected_count": validation["affected_count"],
            "issue_count": validation["issue_count"],
        },
        "decisions": [
            {
                "action": "validate_submission",
                "result": validation["status"],
                "reason": validation["detail"],
                "source": "deterministic_validation",
            }
        ],
        "questions": questions,
    }


def _questions_from_validation(records, validation):
    questions = []
    for result in validation["records"]:
        if not result["issues"]:
            continue
        record = records[result["index"] - 1]
        for issue in result["issues"]:
            code = issue["code"]
            questions.append(
                {
                    "question_id": f"record-{result['index']}-{code}",
                    "record_index": result["index"],
                    "issue_code": code,
                    "prompt": ISSUE_PROMPTS.get(code, issue["label"]),
                    "context": _record_context(record),
                    "answer": None,
                }
            )
    return questions


def _record_context(record):
    return {
        key: record.get(key, "")
        for key in ("分类", "日期", "金额", "主题", "供应商", "平台", "附件")
        if record.get(key) not in (None, "")
    }


def _step(step_id, title, status):
    return {"id": step_id, "title": title, "status": status}
