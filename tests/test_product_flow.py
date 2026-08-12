from email.message import EmailMessage
from pathlib import Path

import phase2.agent_report as agent_report
import phase2.llm_aggregate as llm_aggregate
import phase2.llm_classify as llm_classify
import phase2.llm_extract as llm_extract


def _mail(subject, sender, body, attachment_name):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message.set_content(body)
    message.add_attachment(
        b"%PDF-1.7 test reimbursement original",
        maintype="application",
        subtype="pdf",
        filename=attachment_name,
    )
    return message.as_bytes()


def test_one_config_one_search_llm_blindspot_date_boundary_and_package(monkeypatch, tmp_path):
    messages = {
        b"1": _mail(
            "12306 购票通知",
            "notice@12306.cn",
            "金额：149.00 日期：2026-06-01 北京→上海",
            "train.pdf",
        ),
        b"2": _mail(
            "Your business stay document",
            "billing@unknown-travel.example",
            "The reimbursement details are contained in this document.",
            "stay.pdf",
        ),
        b"3": _mail(
            "12306 购票通知",
            "notice@12306.cn",
            "金额：88.00 日期：2026-05-31 北京→天津",
            "outside.pdf",
        ),
    }

    class FakeIMAP:
        def __init__(self, server, port):
            assert (server, port) == ("imap.qq.com", 993)

        def login(self, account, password):
            assert (account, password) == ("configured-account", "configured-token")

        def select(self, mailbox):
            assert mailbox == "INBOX"

        def search(self, _charset, query):
            assert query == "SINCE 01-Jun-2026 BEFORE 31-Jul-2026"
            return "OK", [b"1 2 3"]

        def fetch(self, message_id, _query):
            return "OK", [(b"RFC822", messages[message_id])]

        def logout(self):
            return "BYE", []

    classify_calls = []
    extract_calls = []

    def fake_llm_classify(subject, sender, body):
        classify_calls.append(subject)
        return {"category": "发票", "confidence": 0.98, "method": "LLM"}

    def fake_llm_extract(body, category):
        extract_calls.append(category)
        return {
            "分类": "发票",
            "方法": "LLM",
            "金额": 399.0,
            "日期": "2026-07-30",
            "商家": "陌生差旅平台",
        }

    monkeypatch.setattr(agent_report, "get_email_config", lambda: ("configured-account", "configured-token", "imap.qq.com", 993))
    monkeypatch.setattr(agent_report.imaplib, "IMAP4_SSL", FakeIMAP)
    monkeypatch.setattr(agent_report, "llm_available", lambda: True)
    monkeypatch.setattr(llm_classify, "llm_classify", fake_llm_classify)
    monkeypatch.setattr(llm_extract, "llm_extract", fake_llm_extract)
    monkeypatch.setattr(llm_aggregate, "_get_client", lambda: None)

    result = agent_report.main(
        start="2026-06-01",
        end="2026-07-30",
        output_dir=str(tmp_path),
        interactive=False,
    )

    assert result["agent_task"]["status"] == "completed"
    assert [record["日期"] for record in result["records"]] == ["2026-07-30", "2026-06-01"]
    assert sum("LLM" in record["方法"] for record in result["records"]) == 1
    assert classify_calls == ["Your business stay document"]
    assert extract_calls == ["发票"]
    package_dir = Path(result["package_dir"])
    assert Path(result["xlsx_path"]).exists()
    assert {path.name for path in (package_dir / "原件").iterdir()} == {"2_stay.pdf", "3_train.pdf"}
    assert not any("outside" in path.name for path in package_dir.rglob("*"))
