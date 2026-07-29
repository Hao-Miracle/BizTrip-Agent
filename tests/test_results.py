import json
from datetime import datetime

from biztrip_agent.results import write_results_json


def test_write_results_json_persists_summary_and_records(tmp_path):
    records = [
        {"分类": "机票", "金额": 1280.0, "日期": "2026-07-10", "平台": "去哪儿网"},
        {"分类": "酒店", "金额": 598.0, "日期": "2026-07-10", "平台": "华住酒店"},
    ]
    trips = [
        {
            "trip_id": 1,
            "destination": "深圳",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
            "summary": "深圳出差",
            "records": records,
            "total": 1878.0,
            "method": "规则",
        }
    ]

    path = write_results_json(
        records,
        trips,
        tmp_path,
        "2026-07-01~2026-07-29",
        xlsx_path=tmp_path / "report.xlsx",
        review_path=tmp_path / "review.html",
    )

    assert path == tmp_path / f"records_{datetime.now().strftime('%Y%m%d')}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "biztrip.records.v1"
    assert payload["scan_label"] == "2026-07-01~2026-07-29"
    assert payload["summary"]["record_count"] == 2
    assert payload["summary"]["trip_count"] == 1
    assert payload["summary"]["total_amount"] == 1878.0
    assert payload["records"][0]["平台"] == "去哪儿网"
    assert payload["trips"][0]["destination"] == "深圳"
