"""
模块 · LLM 出差聚合
分析所有提取记录，按同一时间段 + 同一目的地归并为一次出差。

这是 Phase 1 完全缺失的能力，LLM 最适合做判断。

用法：
    from phase2.llm_aggregate import aggregate_trips
"""

import os
import json
import re
from datetime import datetime

try:
    from .llm_options import structured_output_options
except ImportError:
    from llm_options import structured_output_options


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


AGGREGATE_PROMPT = """分析以下出差/旅行订单记录，将它们按"行程"分组。

判断同一次出差的依据：
1. 时间接近（日期重叠或前后不超过2天）
2. 目的地相同或邻近（城市级别）
3. 机票的往返自然属于同一次出差

订单记录：
{records}

请按行程分组输出 JSON 数组，每个行程包含：
- trip_id: 从1开始的编号
- destination: 目的地城市
- start_date: 最早日期
- end_date: 最晚日期
- order_indices: 属于该行程的订单序号列表（0-based）
- summary: 一行中文描述（如"甘孜出差 5/27-5/30，含往返机票+酒店+打车"）

只输出 JSON 数组，不要输出其他内容，格式：
[{{"trip_id": 1, "destination": "甘孜", "start_date": "2026-05-27", "end_date": "2026-05-30", "order_indices": [0,1,2], "summary": "..."}}]
"""


def aggregate_trips(records, use_llm=True):
    """
    对所有提取记录进行出差聚合。

    参数:
        records: list of dict，每条记录至少包含 分类、日期、出发地、目的地、金额

    返回:
        trips: list of dict，按 trip_id 分组的行程列表
    """
    if not records:
        return []

    client = _get_client() if use_llm else None

    # LLM 不可用：简单规则聚合（按日期排序后同一目的地归并）
    if client is None:
        return apply_manual_trip_assignments(_rule_aggregate(records), records)

    model = _get_model()

    # 构造简化的记录列表发给 LLM
    simplified = []
    for i, r in enumerate(records):
        simplified.append({
            '序号': i,
            '分类': r.get('分类', ''),
            '日期': r.get('日期', ''),
            '出发地': r.get('出发地', ''),
            '目的地': r.get('目的地', ''),
            '金额': r.get('金额', ''),
            '供应商': r.get('平台', '') or r.get('酒店名称', '') or '',
        })

    try:
        prompt = AGGREGATE_PROMPT.format(
            records=json.dumps(simplified, ensure_ascii=False, indent=2)
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.0,
            max_tokens=1000,
            **structured_output_options(model),
        )
        raw = resp.choices[0].message.content.strip()

        # 提取 JSON 数组
        m = re.search(r'\[[\s\S]*\]', raw)
        if m:
            trips = json.loads(m.group(0))
            return apply_manual_trip_assignments(_normalize_trips(trips, records), records)

    except Exception:
        pass

    # LLM 失败，降级规则
    return apply_manual_trip_assignments(_rule_aggregate(records), records)


def apply_manual_trip_assignments(trips, records):
    """Keep unresolved records unassigned and make explicit user choices authoritative."""
    by_id = {str(trip.get('trip_id')): trip for trip in trips}
    controlled = [
        record for record in records
        if record.get('待确认行程') or record.get('行程归属') not in (None, '')
    ]
    for trip in trips:
        trip['records'] = [record for record in trip.get('records', []) if record not in controlled]

    for record in controlled:
        if record.get('待确认行程'):
            continue
        trip = by_id.get(str(record.get('行程归属')))
        if trip is not None:
            trip.setdefault('records', []).append(record)

    return refresh_trip_totals(trips)


def refresh_trip_totals(trips):
    """Refresh totals without asking the LLM to rebuild unchanged trip groups."""
    for trip in trips:
        trip['total'] = sum(record.get('金额', 0) or 0 for record in trip.get('records', []))
    return trips


def _normalize_trips(trips, records):
    """标准化 LLM 输出的行程数据"""
    result = []
    for t in trips:
        indices = t.get('order_indices', [])
        trip_records = []
        for idx in indices:
            if 0 <= idx < len(records):
                trip_records.append(records[idx])

        total = sum(r.get('金额', 0) or 0 for r in trip_records)

        result.append({
            'trip_id': t.get('trip_id', 0),
            'destination': t.get('destination', ''),
            'start_date': t.get('start_date', ''),
            'end_date': t.get('end_date', ''),
            'summary': t.get('summary', ''),
            'records': trip_records,
            'total': total,
            'method': 'LLM'
        })

    return result


def _rule_aggregate(records):
    """规则兜底：按目的地 + 日期接近简单聚合"""
    if not records:
        return []

    # 先按日期排序
    sorted_records = sorted(records, key=lambda r: _date_key(r.get('日期')))

    # 简单策略：目的地相同且没有明确的跨模式 = 同一趟出差
    trips = []
    current_trip = None

    for r in sorted_records:
        dest = r.get('目的地', '')
        if not dest:
            dest = r.get('出发地', '')  # 如果没有目的地，用出发地判断

        date = _normalized_date(r.get('日期'))

        if current_trip is None:
            current_trip = {
                'destination': dest,
                'start_date': date,
                'end_date': date,
                'records': [r],
            }
        elif dest and current_trip['destination'] == dest:
            current_trip['records'].append(r)
            if date:
                current_trip['end_date'] = max(current_trip['end_date'], date)
                current_trip['start_date'] = min(current_trip['start_date'], date)
        else:
            # 目的地变了，开始新行程
            trips.append(current_trip)
            current_trip = {
                'destination': dest,
                'start_date': date,
                'end_date': date,
                'records': [r],
            }

    if current_trip:
        trips.append(current_trip)

    # 格式化
    result = []
    for i, t in enumerate(trips, 1):
        total = sum(r.get('金额', 0) or 0 for r in t['records'])
        cats = set(r.get('分类', '') for r in t['records'])
        result.append({
            'trip_id': i,
            'destination': t['destination'],
            'start_date': t['start_date'],
            'end_date': t['end_date'],
            'summary': f"目的地: {t['destination']}, 日期: {t['start_date']}~{t['end_date']}, 笔数: {len(t['records'])}, 品类: {','.join(cats)}",
            'records': t['records'],
            'total': total,
            'method': '规则'
        })

    return result


def _normalized_date(value):
    text = str(value or '').strip()
    for format_string in ('%Y-%m-%d', '%Y年%m月%d日'):
        try:
            return datetime.strptime(text, format_string).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return text


def _date_key(value):
    return _normalized_date(value)


if __name__ == '__main__':
    test_records = [
        {'分类': '机票', '日期': '2026-05-27', '出发地': '成都', '目的地': '甘孜', '金额': 1755.0},
        {'分类': '酒店', '日期': '2026-05-27', '酒店名称': '甘孜大酒店', '金额': 598.0},
        {'分类': '网约车', '日期': '2026-05-28', '出发地': '甘孜机场', '目的地': '甘孜县城', '金额': 68.0},
        {'分类': '机票', '日期': '2026-05-30', '出发地': '甘孜', '目的地': '成都', '金额': 1680.0},
        {'分类': '酒店', '日期': '2026-06-15', '酒店名称': '北京酒店', '金额': 880.0},
    ]

    trips = aggregate_trips(test_records)
    print(f'聚合结果（{trips[0]["method"] if trips else "无"}）:')
    for t in trips:
        print(f"\n  Trip #{t['trip_id']}: {t['summary']}")
        print(f"  金额合计: ¥{t['total']:.2f}")
        print(f"  记录数: {len(t['records'])}")
