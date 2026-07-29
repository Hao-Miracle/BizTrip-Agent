"""
模块 · LLM 结构化提取
使用 DeepSeek API 按品类专用 prompt 提取字段，低质量自动降级到正则。

用法：
    from phase2.llm_extract import extract_record

设计：
    - 每个品类有专用 prompt 和 JSON schema
    - LLM 不输出 null/None，缺失字段用空字符串
    - 字段完整性不足时降级到 Phase 1 正则
"""

import os
import json
import re


_client = None


def _get_client():
    """获取 OpenAI 客户端，支持任何 OpenAI 兼容服务商。向下兼容 DEEPSEEK_API_KEY"""
    global _client
    if _client is not None:
        return _client
    api_key = os.getenv('LLM_API_KEY', '') or os.getenv('DEEPSEEK_API_KEY', '')
    if not api_key or api_key.startswith('sk-your-'):
        _client = False
        return None
    base_url = os.getenv('LLM_BASE_URL', '') or os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
    try:
        from openai import OpenAI
    except ImportError:
        _client = False
        return None

    _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _get_model():
    return os.getenv('LLM_MODEL', '') or os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')


# ====== 品类专用 Extract Prompt ======

FLIGHT_PROMPT = """从以下邮件中提取机票信息。

邮件内容：
{body}

提取字段（严格按此 JSON schema 输出）：
{{
  "出行人": "",
  "航班号": "",
  "日期": "YYYY-MM-DD格式",
  "出发地": "",
  "目的地": "",
  "起飞时间": "",
  "到达时间": "",
  "订单号": "",
  "金额": "纯数字，如 1280.00",
  "航空公司": ""
}}

规则：
- 金额取总价（含税总金额），不取单个税费
- 日期统一为 YYYY-MM-DD 格式
- 缺失字段用空字符串，不要输出 null
- 只输出 JSON，不要输出其他内容"""

HOTEL_PROMPT = """从以下邮件中提取酒店预订信息。

邮件内容：
{body}

提取字段（严格按此 JSON schema 输出）：
{{
  "入住人": "",
  "酒店名称": "",
  "入住日期": "YYYY-MM-DD格式",
  "离店日期": "YYYY-MM-DD格式",
  "房型": "",
  "间数": "",
  "金额": "纯数字，如 598.00",
  "订单号": ""
}}

规则：
- 金额取订单总价
- 日期统一为 YYYY-MM-DD 格式
- 缺失字段用空字符串
- 只输出 JSON"""

TRAIN_PROMPT = """从以下邮件中提取火车票信息。

邮件内容：
{body}

提取字段（严格按此 JSON schema 输出）：
{{
  "乘车人": "",
  "车次": "",
  "日期": "YYYY-MM-DD格式",
  "出发站": "",
  "到达站": "",
  "座位等级": "",
  "金额": "纯数字",
  "订单号": ""
}}

规则：
- 车次格式如 G123、D456、C789、Z10
- 金额取票面总价
- 缺失字段用空字符串
- 只输出 JSON"""

TAXI_PROMPT = """从以下邮件中提取网约车/打车信息。

邮件内容：
{body}

提取字段（严格按此 JSON schema 输出）：
{{
  "乘车人": "",
  "日期": "YYYY-MM-DD格式",
  "出发地": "",
  "目的地": "",
  "车型": "",
  "金额": "纯数字",
  "服务商": "滴滴/高德/曹操/T3等"
}}

规则：
- 金额取行程总价（合计金额），不是税费
- 日期统一为 YYYY-MM-DD 格式
- 缺失字段用空字符串
- 只输出 JSON"""

INVOICE_PROMPT = """从以下邮件中提取发票信息。

邮件内容：
{body}

提取字段（严格按此 JSON schema 输出）：
{{
  "日期": "YYYY-MM-DD格式",
  "发票号码": "",
  "金额": "纯数字",
  "商家": "",
  "品类": "油费/餐饮/通行费/其他"
}}

规则：
- 金额取发票总金额
- 品类从邮件中智能判断
- 缺失字段用空字符串
- 只输出 JSON"""

# 品类 → prompt 映射
CATEGORY_PROMPTS = {
    '机票': FLIGHT_PROMPT,
    '酒店': HOTEL_PROMPT,
    '火车票': TRAIN_PROMPT,
    '网约车': TAXI_PROMPT,
    '发票': INVOICE_PROMPT,
    '门票': TAXI_PROMPT,  # 门票字段类似，复用
}


def llm_extract(body, category):
    """LLM 提取单条记录"""
    client = _get_client()
    if client is None:
        return None

    prompt_template = CATEGORY_PROMPTS.get(category)
    if not prompt_template:
        return None

    model = _get_model()

    try:
        prompt = prompt_template.format(body=body[:3000])
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=500,
        )
        raw = resp.choices[0].message.content.strip()

        # 提取 JSON
        m = re.search(r'\{[\s\S]*\}', raw)
        if m:
            result = json.loads(m.group(0))
            return _normalize(result, category)
    except Exception:
        pass

    return None


def _normalize(data, category):
    """标准化 LLM 输出字段"""
    normalized = {
        '分类': category,
        '方法': 'LLM',
        '金额': '',
        '日期': '',
        '出发地': '',
        '目的地': '',
        '订单号': '',
    }
    for k, v in data.items():
        if v is not None and v != '':
            normalized[k] = v

    # 统一金额格式
    amt = normalized.get('金额', '')
    if amt:
        try:
            normalized['金额'] = float(re.sub(r'[^0-9.]', '', str(amt)))
        except:
            normalized['金额'] = ''

    return normalized


def quality_check(llm_result):
    """检查提取质量：关键字段缺失率"""
    key_fields = ['金额', '日期']
    missing = sum(1 for f in key_fields if not llm_result.get(f))
    return missing / len(key_fields) < 0.5  # 允许缺一个关键字段


# ====== 正则降级（精简版，复用 Phase 1 逻辑）======

def rule_extract(body, subject, category):
    """正则兜底提取"""
    data = {'分类': category, '方法': '规则', '金额': '', '日期': ''}

    # 金额
    patterns = [
        r'合[计]\s*(\d+\.?\d*)\s*元',
        r'发票金额[：:]\s*(\d+\.?\d*)',
        r'金额[：:]\s*(\d+\.?\d*)',
        r'价税合计[（(]小写[）)]\s*[¥￥]?\s*(\d+\.?\d*)',
        r'(\d+\.\d{2})\s*元',
        r'[¥￥]\s*(\d+\.?\d*)',
    ]
    for p in patterns:
        m = re.search(p, body)
        if m:
            data['金额'] = float(m.group(1))
            break
    if data['金额'] == '':
        amount = _fallback_12306_amount(body, subject)
        if amount:
            data['金额'] = amount

    # 日期
    for p in [r'(\d{4}年\d{1,2}月\d{1,2}日)', r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})']:
        m = re.search(p, body)
        if m:
            data['日期'] = m.group(1)
            break

    # 路线
    m = re.search(r'([\u4e00-\u9fa5]{2,4})\s*[→\-]\s*([\u4e00-\u9fa5]{2,4})', body)
    if m:
        data['出发地'] = m.group(1)
        data['目的地'] = m.group(2)

    # 订单号
    m = re.search(r'(?:订单|发票)[号编][码号]?[：:（(]?\s*(\w{10,})', body)
    if m:
        data['订单号'] = m.group(1)

    return data


def _fallback_12306_amount(body, subject):
    """Extract ticket amount from 12306 PDFs with garbled currency text."""
    context = f'{subject}\n{body}'.lower()
    if '12306' not in context and 'rails.com.cn' not in context and '网上购票系统' not in context:
        return ''
    amounts = []
    for raw in re.findall(r'(?<!\d)(\d{1,4}\.\d{2})(?!\d)', body):
        try:
            value = float(raw)
        except ValueError:
            continue
        if 1 <= value <= 5000:
            amounts.append(value)
    return max(amounts) if amounts else ''


# ====== 主入口 ======

def extract_record(body, subject, category, use_llm=True):
    """
    提取单条记录。

    策略：
    1. 先尝试 LLM 提取
    2. 质量不合格（关键字段缺失过多）→ 降级到正则
    3. LLM 不可用 → 直接正则
    """
    # 先走 LLM
    llm_result = llm_extract(body, category) if use_llm else None

    if llm_result and quality_check(llm_result):
        return llm_result

    # 降级
    rule_result = rule_extract(body, subject, category)
    if llm_result:
        rule_result['方法'] = 'LLM→规则降级'
    return rule_result


if __name__ == '__main__':
    test_body = """
    您的机票已出票
    航班：CA1234
    日期：2026-05-27
    北京→上海 08:00-10:30
    金额合计：1280.00元
    订单号：QD20260527001
    """

    result = extract_record(test_body, '机票确认单', '机票')
    print(f'提取结果: {json.dumps(result, ensure_ascii=False, indent=2)}')
