"""Persist scan results for later review and regeneration."""

import json
from datetime import datetime
from pathlib import Path


SCHEMA_VERSION = "biztrip.records.v1"


def output_timestamp():
    """Return a readable timestamp for generated report files."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def unique_output_path(directory, stem, suffix):
    """Return a non-overwriting path under directory."""
    directory = Path(directory)
    path = directory / f"{stem}_{output_timestamp()}{suffix}"
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = directory / f"{path.stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def write_results_json(
    records,
    trips,
    output_dir,
    scan_label,
    xlsx_path=None,
    review_path=None,
    agent_task=None,
):
    """Write scan results to a JSON file and return its path."""
    from biztrip_agent.validation import validate_reimbursement

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    total = sum(record.get("金额", 0) or 0 for record in records)
    validation = validate_reimbursement(records, trips)
    path = unique_output_path(output_dir, "records", ".json")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scan_label": scan_label,
        "summary": {
            "record_count": len(records),
            "trip_count": len(trips),
            "total_amount": total,
            "submission_status": validation["status"],
            "can_submit": validation["can_submit"],
            "complete_count": validation["complete_count"],
            "affected_count": validation["affected_count"],
            "issue_count": validation["issue_count"],
        },
        "files": {
            "excel": str(xlsx_path) if xlsx_path else "",
            "review": str(review_path) if review_path else "",
        },
        "records": records,
        "trips": trips,
        "validation": validation,
        "agent_task": agent_task or {},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_results_json(path):
    """Load and validate a BizTrip results JSON file."""
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(f"Unsupported results schema: {schema_version or 'missing'}")
    if not isinstance(payload.get("records"), list):
        raise ValueError("Invalid results file: records must be a list")
    if not isinstance(payload.get("trips"), list):
        raise ValueError("Invalid results file: trips must be a list")
    return payload
