import json
from types import SimpleNamespace

from phase2 import llm_evidence


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **_kwargs):
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _client(content):
    return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(content)))


def test_accepts_high_confidence_candidate_with_exact_quote(monkeypatch):
    monkeypatch.setattr(
        llm_evidence,
        "_get_client",
        lambda: _client(
            '{"candidates":[{"field":"金额","value":"149.00","confidence":0.98,'
            '"quote":"票价合计 149.00 元"}]}'
        ),
    )

    candidates = llm_evidence.resolve_evidence(
        {"_邮件正文": "您的车票信息：票价合计 149.00 元，请查收。"},
        ["missing_amount"],
    )

    assert candidates == [
        {
            "field": "金额",
            "value": 149.0,
            "confidence": 0.98,
            "quote": "票价合计 149.00 元",
        }
    ]


def test_rejects_hallucinated_quote_even_with_high_confidence(monkeypatch):
    monkeypatch.setattr(
        llm_evidence,
        "_get_client",
        lambda: _client(
            '{"candidates":[{"field":"金额","value":"999.00","confidence":0.99,'
            '"quote":"合计 999.00 元"}]}'
        ),
    )

    candidates = llm_evidence.resolve_evidence(
        {"_邮件正文": "您的车票信息没有显示金额。"},
        ["missing_amount"],
    )

    assert candidates == []


def test_rejects_low_confidence_and_value_not_present_in_quote(monkeypatch):
    monkeypatch.setattr(
        llm_evidence,
        "_get_client",
        lambda: _client(
            '{"candidates":['
            '{"field":"供应商","value":"携程","confidence":0.5,"quote":"供应商：携程"},'
            '{"field":"金额","value":"200.00","confidence":0.99,"quote":"合计 100.00 元"}'
            ']}'
        ),
    )

    candidates = llm_evidence.resolve_evidence(
        {"_邮件正文": "供应商：携程，合计 100.00 元"},
        ["missing_vendor", "missing_amount"],
    )

    assert candidates == []


def test_accepts_normalized_date_only_when_same_date_is_in_quote(monkeypatch):
    monkeypatch.setattr(
        llm_evidence,
        "_get_client",
        lambda: _client(
            '{"candidates":[{"field":"日期","value":"2026-08-03","confidence":0.96,'
            '"quote":"开票日期：2026年8月3日"}]}'
        ),
    )

    candidates = llm_evidence.resolve_evidence(
        {"_邮件正文": "电子发票，开票日期：2026年8月3日。"},
        ["missing_date"],
    )

    assert candidates[0]["value"] == "2026-08-03"


def test_rejects_quote_that_copies_excessive_email_content(monkeypatch):
    long_quote = "金额 88.00 元" + ("详细正文" * 60)
    payload = json.dumps(
        {
            "candidates": [
                {
                    "field": "金额",
                    "value": "88.00",
                    "confidence": 0.99,
                    "quote": long_quote,
                }
            ]
        },
        ensure_ascii=False,
    )
    monkeypatch.setattr(llm_evidence, "_get_client", lambda: _client(payload))

    candidates = llm_evidence.resolve_evidence(
        {"_邮件正文": long_quote},
        ["missing_amount"],
    )

    assert candidates == []
