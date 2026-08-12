"""Resolve missing fields from quoted evidence, with deterministic safeguards."""

import json
import re

from .llm_extract import _get_client, _get_model
from .llm_options import structured_output_options


ISSUE_FIELDS = {
    "missing_amount": "金额",
    "missing_date": "日期",
    "missing_vendor": "供应商",
}

SYSTEM_PROMPT = """你是差旅报销证据分析器。只能从提供的原文中寻找缺失字段，禁止推测。
每个候选必须给出原文中连续、逐字一致的短句作为 quote。
无法确定时不要返回该字段。只输出 JSON。"""


def resolve_evidence(record, issue_codes, attachment_text="", min_confidence=0.9):
    """Return candidates whose quote and value can both be verified locally."""
    client = _get_client()
    if client is None:
        return []

    requested = [code for code in issue_codes if code in ISSUE_FIELDS]
    if not requested:
        return []

    evidence = _evidence_text(record, attachment_text)
    if not evidence.strip():
        return []

    fields = [ISSUE_FIELDS[code] for code in requested]
    prompt = f"""待查字段：{json.dumps(fields, ensure_ascii=False)}

原文：
{evidence[:7000]}

输出格式：
{{"candidates": [{{"field": "金额/日期/供应商", "value": "", "confidence": 0.0, "quote": "原文片段"}}]}}
金额只返回数字，日期使用 YYYY-MM-DD。"""

    try:
        model = _get_model()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=600,
            **structured_output_options(model),
        )
        raw = response.choices[0].message.content.strip()
        match = re.search(r"\{[\s\S]*\}", raw)
        payload = json.loads(match.group(0)) if match else {}
    except Exception:
        return []

    verified = []
    allowed_fields = set(fields)
    for candidate in payload.get("candidates", []):
        item = _verify_candidate(candidate, evidence, allowed_fields, min_confidence)
        if item:
            verified.append(item)
    return verified


def _evidence_text(record, attachment_text):
    return "\n".join(
        value
        for value in (
            str(record.get("主题", "") or ""),
            str(record.get("发件人", "") or ""),
            str(record.get("_邮件正文", "") or ""),
            str(attachment_text or ""),
        )
        if value
    )


def _verify_candidate(candidate, evidence, allowed_fields, min_confidence):
    field = str(candidate.get("field", "")).strip()
    value = str(candidate.get("value", "")).strip()
    quote = str(candidate.get("quote", "")).strip()
    try:
        confidence = float(candidate.get("confidence", 0))
    except (TypeError, ValueError):
        return None

    if field not in allowed_fields or not value or not quote or len(quote) > 240:
        return None
    if confidence < min_confidence or quote not in evidence:
        return None

    normalized = _normalize_value(field, value, quote)
    if normalized is None:
        return None
    return {
        "field": field,
        "value": normalized,
        "confidence": confidence,
        "quote": quote,
    }


def _normalize_value(field, value, quote):
    if field == "金额":
        try:
            amount = float(re.sub(r"[^0-9.]", "", value))
        except ValueError:
            return None
        quote_numbers = {
            float(number)
            for number in re.findall(r"(?<!\d)(\d{1,9}(?:\.\d{1,2})?)(?!\d)", quote)
        }
        return amount if amount > 0 and amount in quote_numbers else None
    if field == "日期":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return None
        expected = tuple(int(part) for part in value.split("-"))
        for match in re.finditer(r"(\d{4})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})", quote):
            found = tuple(int(part) for part in match.groups())
            if found == expected:
                return value
        return None
    if field == "供应商":
        return value if value in quote else None
    return None
