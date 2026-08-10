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


def build_agent_task(
    records,
    trips,
    goal,
    use_llm,
    initial_validation=None,
    recovery_actions=None,
):
    """Describe the current goal, completed work and required next decisions."""
    validation = validate_reimbursement(records, trips)
    initial_validation = initial_validation or validation
    recovery_actions = recovery_actions or []
    questions = _questions_from_validation(records, trips, validation)
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
            "initial_issue_count": initial_validation["issue_count"],
            "resolved_issue_count": max(
                0,
                initial_validation["issue_count"] - validation["issue_count"],
            ),
        },
        "decisions": [
            *recovery_actions,
            {
                "action": "validate_submission",
                "result": validation["status"],
                "reason": validation["detail"],
                "source": "deterministic_validation",
            }
        ],
        "questions": questions,
    }


def run_recovery_loop(
    records,
    trips,
    attachment_recoverer=None,
    vendor_resolver=None,
    trip_builder=None,
    evidence_resolver=None,
    max_rounds=2,
):
    """Plan recovery tools from open issues and stop when no progress is made."""
    initial_validation = validate_reimbursement(records, trips)
    validation = initial_validation
    actions = []
    attempted = set()

    for round_number in range(1, max_rounds + 1):
        planned = _plan_recovery(validation, attempted)
        if not planned:
            break

        changed = False
        for item in planned:
            attempted.add((item["record_index"], item["tool"]))
            action = _execute_recovery(
                records,
                item,
                attachment_recoverer=attachment_recoverer,
                vendor_resolver=vendor_resolver,
            )
            action["round"] = round_number
            actions.append(action)
            changed = changed or action["result"] == "recovered"

        if not changed:
            break
        if trip_builder:
            trips = trip_builder(records)
        validation = validate_reimbursement(records, trips)

    evidence_actions = _resolve_with_evidence(records, validation, evidence_resolver)
    actions.extend(evidence_actions)
    if any(action["result"] == "recovered" for action in evidence_actions):
        if trip_builder:
            trips = trip_builder(records)
        validation = validate_reimbursement(records, trips)

    return trips, initial_validation, actions


def recover_record_fields(records, attachment_recoverer=None, vendor_resolver=None):
    """Compatibility helper for callers that do not have trip context."""
    _trips, _validation, actions = run_recovery_loop(
        records,
        [],
        attachment_recoverer=attachment_recoverer,
        vendor_resolver=vendor_resolver,
    )
    return [action for action in actions if action["result"] == "recovered"]


def _questions_from_validation(records, trips, validation):
    questions = []
    for result in validation["records"]:
        if not result["issues"]:
            continue
        record = records[result["index"] - 1]
        codes = [issue["code"] for issue in result["issues"]]
        prompts = [ISSUE_PROMPTS.get(issue["code"], issue["label"]) for issue in result["issues"]]
        questions.append(
            {
                "question_id": f"record-{result['index']}",
                "record_index": result["index"],
                "issue_codes": codes,
                "prompt": " ".join(prompts),
                "context": _record_context(record),
                "options": _question_options(codes, trips),
                "answer": None,
            }
        )
    return questions


def _question_options(codes, trips):
    options = []
    if "unassigned_trip" in codes:
        options.extend(
            {
                "issue_code": "unassigned_trip",
                "value": str(trip.get("trip_id", "")),
                "label": trip.get("summary") or f"行程 {trip.get('trip_id', '')}",
            }
            for trip in trips
            if trip.get("trip_id") not in (None, "")
        )
    if {"possible_duplicate", "identifier_conflict"}.intersection(codes):
        options.append(
            {
                "issue_code": "duplicate_action",
                "value": "exclude",
                "label": "从本次报销排除这条记录",
            }
        )
    return options


def _record_context(record):
    return {
        key: record.get(key, "")
        for key in ("记录ID", "分类", "日期", "金额", "主题", "供应商", "平台", "附件")
        if record.get(key) not in (None, "")
    }


def _copy_first_supported(record, target, sources):
    if record.get(target) not in (None, ""):
        return
    for source in sources:
        value = record.get(source)
        if value not in (None, ""):
            record[target] = value
            return


def _record_vendor(record):
    return record.get("供应商") or record.get("平台") or record.get("酒店名称")


def _plan_recovery(validation, attempted):
    tool_by_issue = {
        "missing_amount": "inspect_attachment",
        "missing_date": "normalize_date",
        "missing_vendor": "resolve_vendor",
    }
    planned = []
    for result in validation["records"]:
        for issue in result["issues"]:
            tool = tool_by_issue.get(issue["code"])
            key = (result["index"], tool)
            if tool and key not in attempted:
                planned.append(
                    {
                        "record_index": result["index"],
                        "issue_code": issue["code"],
                        "tool": tool,
                    }
                )
    return planned


def _execute_recovery(records, plan, attachment_recoverer=None, vendor_resolver=None):
    record = records[plan["record_index"] - 1]
    tool = plan["tool"]
    field = ""
    before = None

    if tool == "inspect_attachment":
        field = "金额"
        before = record.get(field)
        if attachment_recoverer:
            attachment_recoverer([record])
    elif tool == "normalize_date":
        field = "日期"
        before = record.get(field)
        _copy_first_supported(record, field, ("入住日期", "乘车日期", "开票日期", "起飞日期"))
    elif tool == "resolve_vendor":
        field = "供应商" if record.get("分类") in {"发票", "酒店"} else "平台"
        before = record.get(field)
        sources = ("商家", "酒店名称") if field == "供应商" else ("服务商", "航空公司")
        _copy_first_supported(record, field, sources)
        if not _record_vendor(record) and vendor_resolver:
            vendor = vendor_resolver(record)
            if vendor and vendor != "其他":
                record[field] = vendor

    recovered = before in (None, "") and record.get(field) not in (None, "")
    return {
        "action": "use_tool",
        "tool": tool,
        "record_index": plan["record_index"],
        "issue_code": plan["issue_code"],
        "field": field,
        "result": "recovered" if recovered else "no_evidence",
        "value": record.get(field, "") if recovered else "",
        "reason": "找到已有证据" if recovered else "现有材料不足，未修改数据",
        "source": "existing_evidence" if recovered else "none",
    }


def _resolve_with_evidence(records, validation, evidence_resolver):
    if not evidence_resolver:
        return []
    recoverable = {"missing_amount", "missing_date", "missing_vendor"}
    actions = []
    for result in validation["records"]:
        issue_codes = [
            issue["code"]
            for issue in result["issues"]
            if issue["code"] in recoverable
        ]
        if not issue_codes:
            continue
        record = records[result["index"] - 1]
        candidates = evidence_resolver(record, issue_codes) or []
        recovered_fields = set()
        for candidate in candidates:
            field = candidate.get("field")
            target = _target_field(record, field)
            if not target or target in recovered_fields or record.get(target) not in (None, ""):
                continue
            record[target] = candidate.get("value")
            recovered_fields.add(target)
            actions.append(
                {
                    "action": "use_tool",
                    "tool": "llm_evidence_analysis",
                    "record_index": result["index"],
                    "field": target,
                    "result": "recovered",
                    "value": candidate.get("value"),
                    "confidence": candidate.get("confidence"),
                    "evidence_quote": candidate.get("quote"),
                    "reason": "LLM提出候选，本地程序已核对原文证据",
                    "source": "verified_quote",
                }
            )
        if not recovered_fields:
            actions.append(
                {
                    "action": "use_tool",
                    "tool": "llm_evidence_analysis",
                    "record_index": result["index"],
                    "result": "no_evidence",
                    "reason": "未找到通过原文核验的高置信度候选",
                    "source": "none",
                }
            )
    return actions


def _target_field(record, field):
    if field in {"金额", "日期"}:
        return field
    if field == "供应商":
        return "供应商" if record.get("分类") in {"发票", "酒店"} else "平台"
    return ""


def _step(step_id, title, status):
    return {"id": step_id, "title": title, "status": status}
