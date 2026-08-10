"""Validate whether generated reimbursement records are ready to submit."""

from collections import defaultdict
from datetime import datetime
import math
from pathlib import Path


TRIP_CATEGORIES = {"机票", "火车票", "酒店", "网约车", "门票"}
IDENTIFIER_FIELDS = ("订单号", "发票号码", "发票号")
SUPPORTED_ATTACHMENT_SUFFIXES = {".pdf", ".zip", ".jpg", ".jpeg", ".png", ".heic"}


def validate_reimbursement(records, trips, attachment_dir=None):
    """Return a deterministic submission assessment for records and trips."""
    results = [
        {"index": index, "status": "complete", "issues": []}
        for index, _record in enumerate(records, 1)
    ]

    for index, record in enumerate(records):
        if record.get("金额") in (None, ""):
            _add_issue(results[index], "missing_amount", "待补金额")
        elif not _valid_amount(record.get("金额")):
            _add_issue(results[index], "invalid_amount", "金额格式无效")
        if not _text(record.get("日期")):
            _add_issue(results[index], "missing_date", "待补日期")
        elif _parse_date(record.get("日期")) is None:
            _add_issue(results[index], "invalid_date", "日期格式或日期值无效")
        if not _vendor(record):
            _add_issue(results[index], "missing_vendor", "待补供应商")
        if not _text(record.get("附件")):
            _add_issue(results[index], "missing_attachment", "待补原件")
        else:
            _validate_attachment_names(record, results[index], attachment_dir=attachment_dir)
        if record.get("分类") in TRIP_CATEGORIES and not _belongs_to_trip(record, trips):
            _add_issue(results[index], "unassigned_trip", "待确认行程归属")

    _flag_identifier_collisions(records, results)
    _flag_reused_attachments(records, results)
    _validate_trip_integrity(records, trips, results)

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


def _valid_amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(amount) and amount > 0 and round(amount, 2) == amount


def _parse_date(value):
    text = _text(value)
    for format_string in ("%Y-%m-%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(text, format_string).date()
        except ValueError:
            continue
    return None


def _validate_attachment_names(record, result, attachment_dir=None):
    for raw_name in str(record.get("附件") or "").split(";"):
        name = raw_name.strip()
        if not name:
            continue
        path = Path(name)
        if path.name != name or path.suffix.lower() not in SUPPORTED_ATTACHMENT_SUFFIXES:
            _add_issue(result, "invalid_attachment", f"原件名称或格式无效（{name}）")
            continue
        if attachment_dir is not None:
            full_path = Path(attachment_dir) / name
            if not _readable_attachment(full_path, path.suffix.lower()):
                _add_issue(result, "unreadable_attachment", f"原件不存在、为空或无法读取（{name}）")


def _readable_attachment(path, suffix):
    try:
        data = path.read_bytes()[:64]
    except OSError:
        return False
    if not data:
        return False
    checks = {
        ".pdf": data.lstrip().startswith(b"%PDF"),
        ".zip": data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".heic": b"ftyp" in data[:32],
    }
    return checks.get(suffix, False)


def _validate_trip_integrity(records, trips, results):
    memberships = defaultdict(list)
    for trip in trips:
        for trip_record in trip.get("records") or []:
            index = _record_index(records, trip_record)
            if index is not None:
                memberships[index].append(trip)

    for index, assigned_trips in memberships.items():
        if len(assigned_trips) > 1:
            _add_issue(results[index], "multiple_trips", "同一费用被分配到多个行程")

    for trip in trips:
        trip_records = trip.get("records") or []
        if not trip_records:
            continue
        first_index = _record_index(records, trip_records[0])
        start_text = _text(trip.get("start_date"))
        end_text = _text(trip.get("end_date"))
        start_date = _parse_date(start_text) if start_text else None
        end_date = _parse_date(end_text) if end_text else None
        if (start_text and start_date is None) or (end_text and end_date is None):
            if first_index is not None:
                _add_issue(results[first_index], "invalid_trip_dates", "行程起止日期无效")
        elif start_date and end_date and start_date > end_date:
            if first_index is not None:
                _add_issue(results[first_index], "invalid_trip_dates", "行程开始日期晚于结束日期")

        if "total" in trip:
            expected_total = sum(_safe_amount(record.get("金额")) for record in trip_records)
            try:
                actual_total = float(trip.get("total"))
            except (TypeError, ValueError):
                actual_total = None
            if actual_total is None or not math.isfinite(actual_total) or abs(actual_total - expected_total) > 0.01:
                if first_index is not None:
                    _add_issue(results[first_index], "trip_total_mismatch", "行程合计与明细金额不一致")

        if not (start_date and end_date):
            continue
        for trip_record in trip_records:
            index = _record_index(records, trip_record)
            record_date = _parse_date(trip_record.get("日期"))
            if index is not None and record_date and not (start_date <= record_date <= end_date):
                _add_issue(results[index], "date_outside_trip", "费用日期不在所属行程范围内")


def _record_index(records, target):
    target_id = _text(target.get("记录ID"))
    for index, record in enumerate(records):
        record_id = _text(record.get("记录ID"))
        if target_id and record_id:
            if target_id == record_id:
                return index
        elif target is record or target == record:
            return index
    return None


def _safe_amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return 0.0
    return amount if math.isfinite(amount) else 0.0


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
