from biztrip_agent.attachment_match import find_unlinked_attachment
from phase2.agent_report import _cached_attachment_matcher


def test_matches_unlinked_attachment_by_exact_identifier(tmp_path):
    (tmp_path / "invoice_ORDER-8899.pdf").write_bytes(b"not-a-real-pdf")
    record = {
        "订单号": "ORDER-8899",
        "金额": 88.0,
        "日期": "2026-08-01",
        "供应商": "测试商店",
        "附件": "",
    }

    candidate = find_unlinked_attachment(record, [record], tmp_path)

    assert candidate["attachment"] == "invoice_ORDER-8899.pdf"
    assert candidate["signals"] == ["订单号"]


def test_requires_amount_date_and_vendor_without_identifier(tmp_path):
    (tmp_path / "测试商店_2026-08-01_88.00.pdf").write_bytes(b"not-a-real-pdf")
    record = {
        "金额": 88.0,
        "日期": "2026-08-01",
        "供应商": "测试商店",
        "附件": "",
    }

    candidate = find_unlinked_attachment(record, [record], tmp_path)

    assert candidate["attachment"] == "测试商店_2026-08-01_88.00.pdf"
    assert candidate["signals"] == ["金额", "日期", "供应商"]


def test_rejects_ambiguous_or_already_used_candidates(tmp_path):
    (tmp_path / "A_ORDER-8899.pdf").write_bytes(b"not-a-real-pdf")
    (tmp_path / "B_ORDER-8899.pdf").write_bytes(b"not-a-real-pdf")
    record = {"订单号": "ORDER-8899", "附件": ""}

    assert find_unlinked_attachment(record, [record], tmp_path) is None

    (tmp_path / "B_ORDER-8899.pdf").unlink()
    used = {"订单号": "OTHER", "附件": "A_ORDER-8899.pdf"}
    assert find_unlinked_attachment(record, [record, used], tmp_path) is None


def test_cached_matcher_parses_each_candidate_once_per_run(tmp_path, monkeypatch):
    path = tmp_path / "invoice.pdf"
    path.write_bytes(b"not-a-real-pdf")
    calls = []
    monkeypatch.setattr(
        "biztrip_agent.attachment_match._attachment_text",
        lambda candidate: calls.append(candidate) or "ORDER-8899",
    )
    record = {"订单号": "ORDER-8899", "附件": ""}
    matcher = _cached_attachment_matcher(tmp_path)

    assert matcher(record, [record])["attachment"] == "invoice.pdf"
    assert matcher(record, [record])["attachment"] == "invoice.pdf"
    assert calls == [path]
