"""Persist scan results for later review and regeneration."""

import json
from datetime import datetime
from pathlib import Path


def write_results_json(records, trips, output_dir, scan_label, xlsx_path=None, review_path=None):
    """Write scan results to a JSON file and return its path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    total = sum(record.get("金额", 0) or 0 for record in records)
    path = output_dir / f"records_{datetime.now().strftime('%Y%m%d')}.json"

    payload = {
        "schema_version": "biztrip.records.v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scan_label": scan_label,
        "summary": {
            "record_count": len(records),
            "trip_count": len(trips),
            "total_amount": total,
        },
        "files": {
            "excel": str(xlsx_path) if xlsx_path else "",
            "review": str(review_path) if review_path else "",
        },
        "records": records,
        "trips": trips,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
