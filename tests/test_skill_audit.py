import importlib.util
import json
from email.message import EmailMessage
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills" / "biztrip-reimbursement" / "scripts" / "audit_mailbox.py"
SPEC = importlib.util.spec_from_file_location("biztrip_skill_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def test_status_requires_setup_without_downloading(tmp_path, capsys):
    config = tmp_path / "email.json"

    exit_code = AUDIT.main(["status", "--config", str(config)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "setup_required"
    assert not config.exists()


def test_saved_config_is_secret_and_status_becomes_ready(tmp_path, capsys):
    config = tmp_path / "email.json"
    AUDIT.save_config(
        config,
        {"account": "user@qq.com", "password": "mail-token", "server": "imap.qq.com", "port": 993},
    )

    exit_code = AUDIT.main(["status", "--config", str(config)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert json.loads(output)["status"] == "ready"
    assert "mail-token" not in output
    if AUDIT.os.name != "nt":
        assert oct(config.stat().st_mode & 0o777) == "0o600"


def test_public_record_extracts_bounded_audit_evidence():
    message = EmailMessage()
    message["Subject"] = "滴滴行程单 支付金额 88.50元"
    message["From"] = "service@didiglobal.com"
    message["Date"] = "Mon, 10 Aug 2026 12:00:00 +0800"
    message.set_content("本次行程支付金额 88.50元。")
    message.add_attachment(b"pdf", maintype="application", subtype="pdf", filename="trip.pdf")

    record = AUDIT.public_record(message)

    assert record["category"] == "网约车"
    assert record["amount_candidates"][0] == 88.5
    assert record["attachment_names"] == ["trip.pdf"]
    assert record["issue_codes"] == []


def test_audit_range_is_bounded():
    assert AUDIT.range_error("2026-07-01", "2026-08-01", 60)
    assert AUDIT.range_error(None, None, 61)
    assert AUDIT.range_error("2026-07-01", "2026-07-31", 60) == ""


def test_audit_is_read_only_and_never_returns_package(tmp_path, capsys, monkeypatch):
    message = EmailMessage()
    message["Subject"] = "12306 车票 149.00元"
    message["From"] = "notice@12306.cn"
    message["Date"] = "Mon, 10 Aug 2026 12:00:00 +0800"
    message.set_content("高铁订单金额 149.00元")
    calls = {}

    class FakeIMAP:
        def __init__(self, server, port):
            calls["server"] = server
            calls["port"] = port

        def login(self, account, password):
            calls["login"] = (account, password)

        def select(self, mailbox, readonly=False):
            calls["readonly"] = readonly

        def search(self, _charset, *_args):
            return "OK", [b"1"]

        def fetch(self, _message_id, _query):
            return "OK", [(b"RFC822", message.as_bytes())]

        def logout(self):
            return "BYE", []

    config = tmp_path / "email.json"
    AUDIT.save_config(
        config,
        {"account": "user@qq.com", "password": "mail-token", "server": "imap.qq.com", "port": 993},
    )
    monkeypatch.setattr(AUDIT.imaplib, "IMAP4_SSL", FakeIMAP)

    exit_code = AUDIT.main(["audit", "--config", str(config), "--count", "60"])
    output = capsys.readouterr().out
    payload = json.loads(output)

    assert exit_code == 0
    assert calls["readonly"] is True
    assert payload["status"] == "audit_ready"
    assert payload["summary"]["candidate_total"] == 149.0
    assert payload["files"] == {"excel": "", "package_dir": ""}
    assert "mail-token" not in output


def test_skill_has_no_secondary_engine_installation():
    skill = (SCRIPT.parents[1] / "SKILL.md").read_text(encoding="utf-8")

    assert "audit_mailbox.py" in skill
    assert "install_engine.py" not in skill
    assert "pip install" not in skill
    assert "biztrip agent audit" not in skill
