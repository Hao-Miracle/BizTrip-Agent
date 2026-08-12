from datetime import datetime

from common.utils import format_chinese_date
from phase2.llm_classify import classify_email
from phase2.llm_extract import extract_record
from phase2.llm_aggregate import aggregate_trips
from phase2.llm_options import structured_output_options
import phase2.llm_classify as llm_classify_module
import phase2.llm_extract as llm_extract_module


def test_classifies_known_travel_platforms_without_llm():
    cases = [
        ("service@qunar.com", "机票确认单", "机票"),
        ("noreply@huazhuhotels.com", "酒店预订成功", "酒店"),
        ("notice@xiaojukeji.com", "滴滴行程单", "网约车"),
        ("service@crestv.cn", "电子发票", "发票"),
    ]

    for sender, subject, expected in cases:
        result = classify_email(subject, sender, "", use_llm=False)
        assert result["category"] == expected


def test_llm_classification_only_handles_rule_unknowns(monkeypatch):
    calls = []
    monkeypatch.setattr(
        llm_classify_module,
        "llm_classify",
        lambda subject, sender, body: calls.append(subject) or {"category": "酒店", "confidence": 0.95, "method": "LLM"},
    )

    known = classify_email("酒店预订成功", "noreply@huazhuhotels.com", "", use_llm=True)
    unknown = classify_email("Your itinerary is ready", "travel@example.net", "住宿确认", use_llm=True)

    assert known["method"] != "LLM"
    assert unknown["method"] == "LLM"
    assert calls == ["Your itinerary is ready"]


def test_llm_extraction_only_fills_incomplete_rule_result(monkeypatch):
    calls = []
    monkeypatch.setattr(
        llm_extract_module,
        "llm_extract",
        lambda body, category: calls.append(body) or {"分类": category, "方法": "LLM", "金额": 299.0, "日期": "2026-07-08"},
    )

    complete = extract_record("金额：88.00 日期：2026-07-07", "发票", "发票", use_llm=True)
    incomplete = extract_record("住宿确认，信息见附件", "酒店确认", "酒店", use_llm=True)

    assert complete["方法"] == "规则"
    assert incomplete["方法"] == "LLM补全"
    assert calls == ["住宿确认，信息见附件"]


def test_deepseek_v4_structured_calls_disable_thinking():
    assert structured_output_options("deepseek-v4-flash") == {"extra_body": {"enable_thinking": False}}
    assert structured_output_options("example-chat") == {}


def test_rule_aggregation_normalizes_dates_and_keeps_unknown_destinations_separate():
    records = [
        {"分类": "发票", "日期": "2026年06月02日", "目的地": "", "金额": 10},
        {"分类": "发票", "日期": "2026-06-01", "目的地": "", "金额": 20},
    ]

    trips = aggregate_trips(records, use_llm=False)

    assert len(trips) == 2
    assert [trip["start_date"] for trip in trips] == ["2026-06-01", "2026-06-02"]


def test_skips_irrelevant_email_without_llm():
    result = classify_email("Steam 夏季促销", "news@steampowered.com", "", use_llm=False)

    assert result["category"] == "不相关"


def test_travel_platform_domain_does_not_make_marketing_email_a_flight():
    result = classify_email(
        "【功能介绍】会员体系互通：快速升级 权益尽享(AD)",
        "newsletter@ctrip.com",
        "会员权益介绍",
        use_llm=False,
    )

    assert result["category"] == "不相关"


def test_invalid_rule_date_triggers_llm_recovery(monkeypatch):
    calls = []
    monkeypatch.setattr(
        llm_extract_module,
        "llm_extract",
        lambda body, category: calls.append(body)
        or {"分类": category, "方法": "LLM", "金额": 111.3, "日期": "2022-08-25"},
    )

    result = extract_record("金额：111.30 日期：2252-08/25", "高德打车电子发票", "发票", use_llm=True)

    assert result["日期"] == "2022-08-25"
    assert result["方法"] == "LLM补全"
    assert len(calls) == 1


def test_invalid_date_is_not_restored_when_llm_cannot_recover(monkeypatch):
    monkeypatch.setattr(llm_extract_module, "llm_extract", lambda _body, _category: None)

    result = extract_record("金额：7.60 日期：6773-99-2", "高德打车电子发票", "网约车", use_llm=True)

    assert result["日期"] == ""


def test_high_de_taxi_invoice_is_classified_as_taxi():
    result = classify_email("高德打车电子发票", "invoice@example.com", "", use_llm=False)

    assert result["category"] == "网约车"


def test_extracts_flight_amount_date_and_route_without_llm():
    body = "您的机票已出票。金额1280.00元 日期：2026-07-10 上海→深圳 订单号：QD20260710001"

    result = extract_record(body, "机票确认单", "机票", use_llm=False)

    assert result["分类"] == "机票"
    assert result["金额"] == 1280.0
    assert result["日期"] == "2026-07-10"
    assert result["出发地"] == "上海"
    assert result["目的地"] == "深圳"
    assert result["订单号"] == "QD20260710001"


def test_extracts_taxi_amount_date_and_route_without_llm():
    body = "滴滴行程单 合计86.50元 日期：2026-07-10 机场→酒店"

    result = extract_record(body, "滴滴行程单", "网约车", use_llm=False)

    assert result["金额"] == 86.5
    assert result["日期"] == "2026-07-10"
    assert result["出发地"] == "机场"
    assert result["目的地"] == "酒店"


def test_extracts_invoice_amount_and_date_without_llm():
    body = "电子发票 发票金额：136.00 日期：2026年7月11日"

    result = extract_record(body, "餐饮电子发票", "发票", use_llm=False)

    assert result["金额"] == 136.0
    assert result["日期"] == "2026年7月11日"


def test_chinese_date_format_does_not_depend_on_system_locale():
    assert format_chinese_date(datetime(2026, 8, 7)) == "2026年08月07日"


def test_extracts_12306_amount_from_garbled_pdf_text_without_llm():
    body = "12306 SÑyhS÷x\x01 :26519146126000331196\nXichangxiD252\n2026^t07g\x0815eå\nyhN÷:ÿå149.00N\x8c{I"

    result = extract_record(body, "网上购票系统-电子发票通知", "发票", use_llm=False)

    assert result["金额"] == 149.0


def test_rule_aggregate_groups_by_destination_without_llm():
    records = [
        {"分类": "机票", "日期": "2026-07-10", "出发地": "上海", "目的地": "深圳", "金额": 1280.0},
        {"分类": "网约车", "日期": "2026-07-10", "出发地": "机场", "目的地": "深圳", "金额": 86.5},
    ]

    trips = aggregate_trips(records, use_llm=False)

    assert len(trips) == 1
    assert trips[0]["destination"] == "深圳"
    assert trips[0]["total"] == 1366.5
