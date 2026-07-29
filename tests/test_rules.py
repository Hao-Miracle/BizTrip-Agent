from phase2.llm_classify import classify_email
from phase2.llm_extract import extract_record
from phase2.llm_aggregate import aggregate_trips


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


def test_skips_irrelevant_email_without_llm():
    result = classify_email("Steam 夏季促销", "news@steampowered.com", "", use_llm=False)

    assert result["category"] == "不相关"


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
