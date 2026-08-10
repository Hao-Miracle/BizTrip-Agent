"""Stable JSON interface for agent skills and other local orchestrators."""

import io
import json
import os
from contextlib import redirect_stdout
from pathlib import Path

from biztrip_agent.results import load_results_json


INTERFACE_SCHEMA = "biztrip.agent-interface.v1"
AUDIT_SCHEMA = "biztrip.audit.v1"
AUDIT_RECORD_LIMIT = 20


def audit_task(start=None, end=None, count=60, output_dir="output"):
    """Run a rules-only reimbursement audit without creating a final package."""
    try:
        from phase2.agent_report import main as run_agent

        if not _email_configured():
            return _failure(
                "audit",
                "setup_required",
                "请先在本地 Web 页面完成邮箱账号和授权码配置。",
                schema=AUDIT_SCHEMA,
            )
        with redirect_stdout(io.StringIO()):
            result = run_agent(
                start=start,
                end=end,
                count=count,
                no_llm=True,
                output_dir=output_dir,
                interactive=False,
                review=False,
                deliver=False,
            )
    except Exception as exc:
        return _failure("audit", "engine_error", _safe_error(exc), schema=AUDIT_SCHEMA)
    if not result or not result.get("results_path"):
        return _failure(
            "audit",
            "audit_not_created",
            "体检没有完成。请在本地 Web 页面检查邮箱配置和连接状态。",
            schema=AUDIT_SCHEMA,
        )
    return audit_snapshot(result["results_path"])


def start_task(start=None, end=None, count=60, no_llm=False, output_dir="output"):
    """Run one scan quietly and return a machine-readable task snapshot."""
    try:
        from phase2.agent_report import main as run_agent

        if not _agent_configured():
            return _failure(
                "start",
                "setup_required",
                "请先在本地 Web 页面完成邮箱和 Agent 模型配置。",
            )
        with redirect_stdout(io.StringIO()):
            result = run_agent(
                start=start,
                end=end,
                count=count,
                no_llm=no_llm,
                output_dir=output_dir,
                interactive=False,
                review=False,
            )
    except Exception as exc:
        return _failure("start", "engine_error", _safe_error(exc))
    if not result or not result.get("results_path"):
        return _failure(
            "start",
            "task_not_created",
            "任务没有完成。请先在本地 Web 页面检查邮箱配置和连接状态。",
        )
    return task_snapshot(result["results_path"], operation="start")


def task_status(task_path=None, output_dir="output"):
    """Return the latest task or one explicitly selected task."""
    path = Path(task_path).expanduser() if task_path else latest_task_path(output_dir)
    if not path:
        return _failure("status", "task_not_found", "还没有可查询的报销任务。")
    return task_snapshot(path, operation="status")


def answer_task(task_path, answers, output_dir=None):
    """Apply explicit user answers and return the newly verified task snapshot."""
    try:
        normalized = normalize_answers(answers)
        from biztrip_agent.resolution import resolve_results

        result = resolve_results(task_path, normalized, output_dir=output_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _failure("answer", "invalid_answer", _safe_error(exc), task_path)
    return task_snapshot(result["results_path"], operation="answer")


def task_snapshot(task_path, operation="status"):
    """Convert an internal task file into the public Agent interface schema."""
    path = Path(task_path).expanduser().resolve()
    try:
        payload = load_results_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _failure(operation, "task_unreadable", _safe_error(exc), path)

    task = payload.get("agent_task", {})
    status = task.get("status") or _status_from_summary(payload.get("summary", {}))
    files = payload.get("files", {})
    excel = files.get("excel") or ""
    package_dir = str(Path(excel).parent) if excel else ""
    return {
        "schema_version": INTERFACE_SCHEMA,
        "operation": operation,
        "ok": True,
        "status": status,
        "task_path": str(path),
        "summary": {
            "scan_label": payload.get("scan_label", ""),
            "record_count": payload.get("summary", {}).get("record_count", 0),
            "trip_count": payload.get("summary", {}).get("trip_count", 0),
            "total_amount": payload.get("summary", {}).get("total_amount", 0),
            "issue_count": payload.get("summary", {}).get("issue_count", 0),
        },
        "questions": [_public_question(question) for question in task.get("questions", [])],
        "files": {
            "package_dir": package_dir,
            "excel": excel,
        },
        "next_action": _next_action(status),
    }


def latest_task_path(output_dir):
    """Find the newest internal task without reading user configuration."""
    root = Path(output_dir).expanduser()
    files = [*root.glob("records_*.json"), *(root / ".biztrip").glob("records_*.json")]
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


def normalize_answers(payload):
    """Accept a JSON answer list and convert it to the engine's internal key form."""
    items = payload.get("answers") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("answers 必须是列表。")
    answers = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("每条 answer 必须是对象。")
        try:
            index = int(item.get("record_index"))
        except (TypeError, ValueError) as exc:
            raise ValueError("record_index 必须是正整数。") from exc
        issue_code = str(item.get("issue_code") or "").strip()
        if index < 1 or not issue_code:
            raise ValueError("answer 缺少有效的 record_index 或 issue_code。")
        answers[(index, issue_code)] = item.get("value")
    if not answers:
        raise ValueError("没有提供任何确认信息。")
    return answers


def _public_question(question):
    return {
        "question_id": question.get("question_id", ""),
        "record_index": question.get("record_index", 0),
        "issue_codes": question.get("issue_codes", []),
        "prompt": question.get("prompt", ""),
        "context": question.get("context", {}),
        "options": question.get("options", []),
        "attachment_requires_web": any(
            code in {"missing_attachment", "unreadable_attachment"}
            for code in question.get("issue_codes", [])
        ),
    }


def _status_from_summary(summary):
    return "completed" if summary.get("can_submit") else "needs_user_input"


def _next_action(status):
    if status == "completed":
        return "deliver_package"
    if status == "needs_user_input":
        return "ask_user"
    return "inspect_error"


def _failure(operation, code, message, task_path=None, schema=INTERFACE_SCHEMA):
    return {
        "schema_version": schema,
        "operation": operation,
        "ok": False,
        "status": "failed",
        "task_path": str(task_path or ""),
        "error": {"code": code, "message": message},
        "next_action": "inspect_error",
    }


def _safe_error(exc):
    message = str(exc).strip()
    return message[:500] if message else exc.__class__.__name__


def _email_configured():
    from common.utils import get_email_config

    account, password, _server, _port = get_email_config()
    return bool(account and password)


def _agent_configured():
    return bool(
        _email_configured()
        and os.getenv("LLM_API_KEY")
        and os.getenv("LLM_BASE_URL")
        and os.getenv("LLM_MODEL")
    )


def audit_snapshot(task_path):
    """Return a bounded, non-secret summary for the host Agent to explain."""
    path = Path(task_path).expanduser().resolve()
    try:
        payload = load_results_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _failure("audit", "audit_unreadable", _safe_error(exc), schema=AUDIT_SCHEMA)

    records = payload.get("records", [])
    validation_records = {
        item.get("index"): item.get("issues", [])
        for item in payload.get("validation", {}).get("records", [])
    }
    categories = {}
    public_records = []
    for index, record in enumerate(records, 1):
        category = str(record.get("分类") or "其他")
        bucket = categories.setdefault(category, {"count": 0, "amount": 0})
        bucket["count"] += 1
        bucket["amount"] += record.get("金额", 0) or 0
        if len(public_records) < AUDIT_RECORD_LIMIT:
            public_records.append(_public_audit_record(index, record, validation_records.get(index, [])))

    summary = payload.get("summary", {})
    return {
        "schema_version": AUDIT_SCHEMA,
        "operation": "audit",
        "ok": True,
        "status": "audit_ready",
        "summary": {
            "scan_label": payload.get("scan_label", ""),
            "record_count": summary.get("record_count", 0),
            "trip_count": summary.get("trip_count", 0),
            "total_amount": summary.get("total_amount", 0),
            "complete_record_count": summary.get("complete_count", 0),
            "affected_record_count": summary.get("affected_count", 0),
            "issue_count": summary.get("issue_count", 0),
        },
        "categories": categories,
        "trips": [_public_audit_trip(trip) for trip in payload.get("trips", [])],
        "records": public_records,
        "records_truncated": len(records) > AUDIT_RECORD_LIMIT,
        "files": {"package_dir": "", "excel": ""},
        "next_action": "present_audit",
        "full_package": {
            "requires": "local_personal_app",
            "message": "安装本地个人版后可生成完整 Excel 和原件报销包。",
        },
    }


def _public_audit_record(index, record, issues):
    return {
        "record_index": index,
        "category": record.get("分类", ""),
        "date": record.get("日期") or record.get("入住日期") or "",
        "vendor": record.get("供应商") or record.get("平台") or record.get("商家") or "",
        "amount": record.get("金额", ""),
        "route": _audit_route(record),
        "issue_codes": [issue.get("code", "") for issue in issues],
    }


def _public_audit_trip(trip):
    return {
        "trip_id": trip.get("trip_id", ""),
        "destination": trip.get("destination", ""),
        "start_date": trip.get("start_date", ""),
        "end_date": trip.get("end_date", ""),
        "total": trip.get("total", 0),
        "summary": trip.get("summary", ""),
    }


def _audit_route(record):
    start = record.get("出发地") or record.get("上车地点") or ""
    end = record.get("目的地") or record.get("下车地点") or ""
    return f"{start}→{end}" if start and end else start or end
