"""Generate local HTML review reports for extracted trip records."""

from collections import defaultdict
from datetime import datetime
from html import escape
from pathlib import Path

from biztrip_agent.results import unique_output_path


def generate_review_html(records, trips, output_dir, scan_label, excel_path=None):
    """Write a self-contained HTML review page and return its path."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = sum(record.get("金额", 0) or 0 for record in records)
    issues = _issue_rows(records)
    categories = _category_totals(records)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    review_path = unique_output_path(output_dir, "review", ".html")

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizTrip Agent Review</title>
  <style>
    :root {{
      color-scheme: light;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #d1d5db;
      --soft: #f3f4f6;
      --blue: #1a56db;
      --green: #047857;
      --red: #b91c1c;
      --yellow: #92400e;
      --white: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--white);
      line-height: 1.5;
    }}
    header {{
      padding: 28px 32px 20px;
      border-bottom: 1px solid var(--line);
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    h2 {{ margin: 28px 0 12px; font-size: 18px; }}
    main {{ padding: 0 32px 36px; }}
    .meta {{ color: var(--muted); font-size: 13px; }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(140px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .metric {{
      border: 1px solid var(--line);
      padding: 14px;
      min-height: 82px;
      background: var(--white);
    }}
    .metric-label {{ color: var(--muted); font-size: 13px; }}
    .metric-value {{ margin-top: 6px; font-size: 22px; font-weight: 700; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      border: 1px solid var(--line);
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    th {{
      background: var(--blue);
      color: var(--white);
      font-weight: 700;
    }}
    tr:nth-child(even) td {{ background: #f9fafb; }}
    .amount {{ text-align: right; white-space: nowrap; }}
    .badge {{
      display: inline-block;
      padding: 2px 7px;
      border: 1px solid var(--line);
      font-size: 12px;
      color: var(--muted);
      background: var(--white);
    }}
    .ok {{ color: var(--green); border-color: #a7f3d0; background: #ecfdf5; }}
    .warn {{ color: var(--yellow); border-color: #fde68a; background: #fffbeb; }}
    .bad {{ color: var(--red); border-color: #fecaca; background: #fef2f2; }}
    .note {{
      color: var(--muted);
      font-size: 13px;
      margin: 6px 0 14px;
    }}
    a {{ color: var(--blue); text-decoration: none; }}
    @media (max-width: 760px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(120px, 1fr)); }}
      table {{ display: block; overflow-x: auto; white-space: nowrap; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>BizTrip Agent 审阅报告</h1>
    <div class="meta">生成时间：{escape(generated_at)} · 扫描范围：{escape(scan_label)}{_excel_link(excel_path)}</div>
    <section class="metrics">
      <div class="metric"><div class="metric-label">可报销总额</div><div class="metric-value">¥ {total:,.2f}</div></div>
      <div class="metric"><div class="metric-label">记录数</div><div class="metric-value">{len(records)}</div></div>
      <div class="metric"><div class="metric-label">行程数</div><div class="metric-value">{len(trips)}</div></div>
      <div class="metric"><div class="metric-label">需检查</div><div class="metric-value">{len(issues)}</div></div>
    </section>
  </header>
  <main>
    <h2>需检查项</h2>
    <p class="note">金额、日期或附件缺失的记录会出现在这里。报销前优先核对这些行。</p>
    {_issues_table(issues)}
    <h2>按类别汇总</h2>
    {_category_table(categories, total)}
    <h2>行程汇总</h2>
    {_trip_table(trips)}
    <h2>费用明细</h2>
    {_records_table(records)}
  </main>
</body>
</html>
"""
    review_path.write_text(html, encoding="utf-8")
    return review_path


def _excel_link(excel_path):
    if not excel_path:
        return ""
    path = Path(excel_path)
    return f' · Excel：<a href="{escape(path.name)}">{escape(path.name)}</a>'


def _issue_rows(records):
    issues = []
    for index, record in enumerate(records, 1):
        missing = []
        if not record.get("金额"):
            missing.append("缺金额")
        if not record.get("日期"):
            missing.append("缺日期")
        if not record.get("附件"):
            missing.append("无附件")
        if missing:
            issues.append((index, record, missing))
    return issues


def _category_totals(records):
    totals = defaultdict(lambda: {"count": 0, "amount": 0})
    for record in records:
        category = record.get("分类") or "其他"
        totals[category]["count"] += 1
        totals[category]["amount"] += record.get("金额", 0) or 0
    return sorted(totals.items(), key=lambda item: -item[1]["amount"])


def _issues_table(issues):
    if not issues:
        return '<p><span class="badge ok">未发现明显缺失字段</span></p>'
    rows = []
    for index, record, missing in issues:
        missing_badges = "".join(
            f'<span class="badge bad">{escape(item)}</span> '
            for item in missing
        )
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(record.get('日期') or '-')}</td>"
            f"<td>{escape(record.get('分类') or '-')}</td>"
            f"<td>{escape(_vendor(record))}</td>"
            f"<td class=\"amount\">{_amount(record)}</td>"
            f"<td>{missing_badges}</td>"
            "</tr>"
        )
    return _table(["序号", "日期", "类别", "供应商/平台", "金额", "问题"], rows)


def _category_table(categories, total):
    rows = []
    for category, data in categories:
        pct = f"{data['amount'] / total * 100:.1f}%" if total else "0.0%"
        rows.append(
            "<tr>"
            f"<td>{escape(category)}</td>"
            f"<td>{data['count']}</td>"
            f"<td class=\"amount\">¥ {data['amount']:,.2f}</td>"
            f"<td>{pct}</td>"
            "</tr>"
        )
    return _table(["类别", "笔数", "金额", "占比"], rows)


def _trip_table(trips):
    if not trips:
        return '<p><span class="badge warn">未识别到行程分组</span></p>'
    rows = []
    for trip in trips:
        rows.append(
            "<tr>"
            f"<td>Trip #{escape(str(trip.get('trip_id', '-')))}</td>"
            f"<td>{escape(trip.get('destination') or '-')}</td>"
            f"<td>{escape(trip.get('start_date') or '-')} ~ {escape(trip.get('end_date') or '-')}</td>"
            f"<td>{len(trip.get('records') or [])}</td>"
            f"<td class=\"amount\">¥ {(trip.get('total') or 0):,.2f}</td>"
            f"<td>{escape(trip.get('summary') or '-')}</td>"
            "</tr>"
        )
    return _table(["行程", "目的地", "日期", "记录数", "金额", "摘要"], rows)


def _records_table(records):
    rows = []
    for index, record in enumerate(sorted(records, key=lambda item: str(item.get("日期") or "")), 1):
        route = _route(record)
        status = '<span class="badge ok">OK</span>' if not _issue_rows([record]) else '<span class="badge warn">检查</span>'
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{escape(record.get('日期') or '-')}</td>"
            f"<td>{escape(record.get('分类') or '-')}</td>"
            f"<td>{escape(_vendor(record))}</td>"
            f"<td class=\"amount\">{_amount(record)}</td>"
            f"<td>{escape(route)}</td>"
            f"<td>{escape(record.get('方法') or '-')}</td>"
            f"<td>{escape(record.get('附件') or '-')}</td>"
            f"<td>{status}</td>"
            "</tr>"
        )
    return _table(["序号", "日期", "类别", "供应商/平台", "金额", "路线", "方法", "附件", "状态"], rows)


def _table(headers, rows):
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = "\n".join(rows)
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"


def _vendor(record):
    return record.get("酒店名称") or record.get("供应商") or record.get("平台") or "其他"


def _route(record):
    if record.get("出发地") and record.get("目的地"):
        return f"{record.get('出发地')}→{record.get('目的地')}"
    if record.get("目的地"):
        return str(record.get("目的地"))
    return "-"


def _amount(record):
    amount = record.get("金额")
    if amount in ("", None):
        return "-"
    return f"¥ {float(amount):,.2f}"
