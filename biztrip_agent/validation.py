"""Validate whether generated reimbursement records are ready to submit."""

from collections import defaultdict


TRIP_CATEGORIES = {"机票", "火车票", "酒店", "网约车", "门票"}
IDENTIFIER_FIELDS = ("订单号", "发票号码", "发票号")


def validate_reimbursement(records, trips):
    """Return a deterministic submission assessment for records and trips."""
    results = [
        {"index": index, "status": "complete", "issues": []}
        for index, _record in enumerate(records, 1)
    ]

    for index, record in enumerate(records):
        if not _has_amount(record):
            _add_issue(results[index], "missing_amount", "待补金额")
        if not _text(record.get("日期")):
            _add_issue(results[index], "missing_date", "待补日期")
        if not _vendor(record):
            _add_issue(results[index], "missing_vendor", "待补供应商")
        if not _text(record.get("附件")):
            _add_issue(results[index], "missing_attachment", "待补原件")
        if record.get("分类") in TRIP_CATEGORIES and not _belongs_to_trip(record, trips):
            _add_issue(results[index], "unassigned_trip", "待确认行程归属")

    _flag_identifier_collisions(records, results)
    _flag_reused_attachments(records, results)

    for result in results:
        if result["issues"]:
            result["status"] = "needs_review"

    issue_count = sum(len(result["issues"]) for result in results)
    affected_count = sum(result["status"] == "needs_review" for result in results)
    complete_count = len(records) - affected_count
    can_submit = bool(records) and affected_count == 0

    if not records:
        status = "empty"
        title = "没有可提交的记录"
        detail = "当前范围没有识别到报销记录，请检查查询时间。"
    elif can_submit:
        status = "ready"
        title = "可以提交"
        detail = f"{len(records)} 条记录均通过完整性检查。"
    else:
        status = "needs_review"
        title = "暂不建议提交"
        detail = f"{affected_count} 条记录需要处理，共发现 {issue_count} 个问题。"

    return {
        "status": status,
        "can_submit": can_submit,
        "title": title,
        "detail": detail,
        "record_count": len(records),
        "complete_count": complete_count,
        "affected_count": affected_count,
        "issue_count": issue_count,
        "records": results,
    }


def _flag_identifier_collisions(records, results):
    groups = defaultdict(list)
    for index, record in enumerate(records):
        for field in IDENTIFIER_FIELDS:
            value = _text(record.get(field))
            if value:
                groups[(field, value)].append(index)

    for (field, value), indices in groups.items():
        if len(indices) < 2:
            continue
        conflict = _has_material_conflict([records[index] for index in indices])
        code = "identifier_conflict" if conflict else "possible_duplicate"
        label = f"{field} {value} 数据冲突" if conflict else f"疑似重复（{field} {value}）"
        for index in indices:
            _add_issue(results[index], code, label)


def _flag_reused_attachments(records, results):
    groups = defaultdict(list)
    for index, record in enumerate(records):
        attachment = _text(record.get("附件"))
        if attachment:
            groups[attachment].append(index)

    for attachment, indices in groups.items():
        if len(indices) < 2:
            continue
        for index in indices:
            _add_issue(results[index], "possible_duplicate", f"疑似重复使用原件（{attachment}）")


def _has_material_conflict(records):
    for field in ("金额", "日期", "出发地", "目的地", "供应商", "平台", "酒店名称"):
        values = {_normalized_value(record.get(field)) for record in records}
        values.discard("")
        if len(values) > 1:
            return True
    return False


def _belongs_to_trip(record, trips):
    for trip in trips:
        for trip_record in trip.get("records") or []:
            if trip_record is record or trip_record == record:
                return True
    return False


def _has_amount(record):
    amount = record.get("金额")
    if amount in (None, ""):
        return False
    try:
        return float(amount) > 0
    except (TypeError, ValueError):
        return False


def _vendor(record):
    return _text(record.get("酒店名称") or record.get("供应商") or record.get("平台"))


def _text(value):
    return str(value).strip() if value not in (None, "") else ""


def _normalized_value(value):
    if isinstance(value, float):
        return f"{value:.2f}"
    return _text(value)


def _add_issue(result, code, label):
    if any(issue["code"] == code and issue["label"] == label for issue in result["issues"]):
        return
    result["issues"].append({"code": code, "label": label, "severity": "error"})
