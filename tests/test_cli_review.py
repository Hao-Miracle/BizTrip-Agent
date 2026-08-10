from pathlib import Path

from openpyxl import load_workbook

from biztrip_agent.cli import main
from biztrip_agent.review import generate_review_html
from biztrip_agent.validation import validate_reimbursement


def test_demo_generates_excel_and_review(tmp_path):
    exit_code = main(["demo", "--review", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    workbook_path = next(tmp_path.glob("差旅汇总_demo_*.xlsx"))
    review_path = next(tmp_path.glob("review_*.html"))
    assert workbook_path.exists()
    assert review_path.exists()

    workbook = load_workbook(workbook_path, data_only=True)
    assert workbook.sheetnames == ["报销总览", "费用明细", "按供应商"]
    assert workbook["报销总览"]["D4"].value == "¥ 2,152.50"

    html = review_path.read_text(encoding="utf-8")
    assert "BizTrip Agent 审阅报告" in html
    assert "未发现需要处理的问题" in html
    assert "可以提交" in html


def test_wizard_generates_demo_with_review(tmp_path, monkeypatch):
    answers = iter(["1", str(tmp_path), "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    exit_code = main(["wizard"])

    assert exit_code == 0
    assert next(tmp_path.glob("差旅汇总_demo_*.xlsx")).exists()
    assert next(tmp_path.glob("review_*.html")).exists()


def test_review_flags_missing_fields(tmp_path):
    records = [
        {
            "分类": "机票",
            "平台": "去哪儿网",
            "金额": "",
            "日期": "",
            "方法": "规则",
            "附件": "",
        }
    ]

    review_path = generate_review_html(records, [], tmp_path, "测试范围", excel_path=Path("report.xlsx"))
    html = review_path.read_text(encoding="utf-8")

    assert "暂不建议提交" in html
    assert "待补金额" in html
    assert "待补日期" in html
    assert "待补原件" in html
    assert "待确认行程归属" in html


def test_validation_flags_duplicates_and_identifier_conflicts():
    records = [
        {
            "分类": "机票",
            "平台": "去哪儿网",
            "金额": 1280.0,
            "日期": "2026-07-10",
            "订单号": "QD001",
            "附件": "flight-a.pdf",
        },
        {
            "分类": "机票",
            "平台": "去哪儿网",
            "金额": 1380.0,
            "日期": "2026-07-10",
            "订单号": "QD001",
            "附件": "flight-b.pdf",
        },
    ]
    trips = [{"records": records}]

    validation = validate_reimbursement(records, trips)

    assert validation["status"] == "needs_review"
    assert validation["affected_count"] == 2
    assert all(
        any(issue["code"] == "identifier_conflict" for issue in result["issues"])
        for result in validation["records"]
    )


def test_validation_marks_complete_records_ready():
    record = {
        "分类": "酒店",
        "酒店名称": "华住酒店",
        "金额": 598.0,
        "日期": "2026-07-10",
        "附件": "hotel.pdf",
    }

    validation = validate_reimbursement([record], [{"records": [record]}])

    assert validation["can_submit"] is True
    assert validation["complete_count"] == 1
    assert validation["issue_count"] == 0
