import json
from datetime import datetime

from openpyxl import load_workbook

from biztrip_agent.cli import main
from biztrip_agent.results import load_results_json, write_results_json


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

    loaded = load_results_json(path)
    assert loaded["summary"]["record_count"] == 2


def test_rebuild_generates_excel_and_review_from_json(tmp_path):
    records = [
        {"分类": "机票", "金额": 1280.0, "日期": "2026-07-10", "平台": "去哪儿网", "方法": "规则", "附件": "flight.pdf"},
        {"分类": "酒店", "金额": 598.0, "日期": "2026-07-10", "平台": "华住酒店", "方法": "规则", "附件": "hotel.pdf"},
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
    source_dir = tmp_path / "source"
    rebuild_dir = tmp_path / "rebuilt"
    source_json = write_results_json(records, trips, source_dir, "测试范围")

    exit_code = main(["rebuild", str(source_json), "--review", "--output-dir", str(rebuild_dir)])

    today = datetime.now().strftime("%Y%m%d")
    workbook_path = rebuild_dir / f"差旅汇总_{today}.xlsx"
    review_path = rebuild_dir / f"review_{today}.html"
    results_path = rebuild_dir / f"records_{today}.json"
    assert exit_code == 0
    assert workbook_path.exists()
    assert review_path.exists()
    assert results_path.exists()

    workbook = load_workbook(workbook_path, data_only=True)
    assert workbook["报销总览"]["D4"].value == "¥ 1,878.00"
    assert "深圳出差" in review_path.read_text(encoding="utf-8")


def test_wizard_rebuilds_from_json(tmp_path, monkeypatch):
    records = [
        {"分类": "机票", "金额": 1280.0, "日期": "2026-07-10", "平台": "去哪儿网", "方法": "规则", "附件": "flight.pdf"},
    ]
    trips = [
        {
            "trip_id": 1,
            "destination": "深圳",
            "start_date": "2026-07-10",
            "end_date": "2026-07-10",
            "summary": "深圳出差",
            "records": records,
            "total": 1280.0,
            "method": "规则",
        }
    ]
    source_json = write_results_json(records, trips, tmp_path / "source", "测试范围")
    rebuild_dir = tmp_path / "rebuilt"
    answers = iter(["2", str(source_json), str(rebuild_dir), "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    exit_code = main(["wizard"])

    today = datetime.now().strftime("%Y%m%d")
    assert exit_code == 0
    assert (rebuild_dir / f"差旅汇总_{today}.xlsx").exists()
    assert (rebuild_dir / f"review_{today}.html").exists()
