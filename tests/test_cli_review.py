from pathlib import Path
from datetime import datetime

from openpyxl import load_workbook

from biztrip_agent.cli import main
from biztrip_agent.review import generate_review_html


def test_demo_generates_excel_and_review(tmp_path):
    exit_code = main(["demo", "--review", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    today = datetime.now().strftime("%Y%m%d")
    workbook_path = tmp_path / f"差旅汇总_demo_{today}.xlsx"
    review_path = tmp_path / f"review_{today}.html"
    assert workbook_path.exists()
    assert review_path.exists()

    workbook = load_workbook(workbook_path, data_only=True)
    assert workbook.sheetnames == ["报销总览", "费用明细", "按供应商"]
    assert workbook["报销总览"]["D4"].value == "¥ 2,152.50"

    html = review_path.read_text(encoding="utf-8")
    assert "BizTrip Agent 审阅报告" in html
    assert "未发现明显缺失字段" in html


def test_wizard_generates_demo_with_review(tmp_path, monkeypatch):
    answers = iter(["1", str(tmp_path), "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    exit_code = main(["wizard"])

    today = datetime.now().strftime("%Y%m%d")
    assert exit_code == 0
    assert (tmp_path / f"差旅汇总_demo_{today}.xlsx").exists()
    assert (tmp_path / f"review_{today}.html").exists()


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

    assert "缺金额" in html
    assert "缺日期" in html
    assert "无附件" in html
