"""BizTrip Agent command-line entry point."""

import argparse
import importlib.util
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_DIR / "output"


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="biztrip",
        description="Scan travel emails and generate reimbursement reports.",
    )
    parser.add_argument("--version", action="version", version="biztrip-agent 0.1.2")

    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo", help="Generate a sample report without reading email.")
    demo_parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for the generated demo report. Defaults to ./output.",
    )

    subparsers.add_parser("check", help="Check Python version, dependencies, and local config.")
    subparsers.add_parser("init", help="Create .env from .env.example if it does not exist.")
    scan_parser = subparsers.add_parser("scan", help="Run the Agent scanner.")
    scan_parser.add_argument("--start", help="Start date in YYYY-MM-DD format.")
    scan_parser.add_argument("--end", help="End date in YYYY-MM-DD format.")
    scan_parser.add_argument("--count", type=int, default=60, help="Number of recent emails to scan when no date range is set.")
    scan_parser.add_argument("--no-llm", action="store_true", help="Force rule mode even when LLM config is present.")
    scan_parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for reports and archived attachments. Defaults to ./output.",
    )

    args = parser.parse_args(argv)
    command = args.command or "demo"

    if command == "demo":
        return demo(Path(args.output_dir))
    if command == "check":
        return check()
    if command == "init":
        return init_config()
    if command == "scan":
        return scan(args)

    parser.print_help()
    return 2


def demo(output_dir):
    """Generate a local Excel report from fictional records."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("Missing dependency: openpyxl")
        print("Install with: pip install -e .")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    records = _demo_records()
    trips = _demo_trips(records)
    total = sum(record["金额"] for record in records)

    wb = Workbook()
    blue = "1A56DB"
    dark = "1F2937"
    header_fill = PatternFill(start_color=blue, end_color=blue, fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11, name="微软雅黑")
    title_font = Font(bold=True, color=dark, size=14, name="微软雅黑")
    body_font = Font(size=10, name="微软雅黑")
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    border = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    ws = wb.active
    ws.title = "报销总览"
    ws.merge_cells("A1:F1")
    ws["A1"] = "差旅费用报销汇总单 · Demo"
    ws["A1"].font = title_font
    ws.merge_cells("A2:F2")
    ws["A2"] = f"生成日期：{datetime.now().strftime('%Y年%m月%d日')} | 示例数据 | 出差相关：{len(records)} 条"
    ws["A2"].font = Font(size=9, color="6B7280", name="微软雅黑")
    ws.merge_cells("A4:C4")
    ws["A4"] = "可报销总额"
    ws["A4"].font = Font(size=12, color="6B7280", name="微软雅黑")
    ws.merge_cells("D4:F4")
    ws["D4"] = f"¥ {total:,.2f}"
    ws["D4"].font = Font(bold=True, size=22, color=blue, name="微软雅黑")
    ws["D4"].alignment = Alignment(horizontal="right", vertical="center")

    row = 6
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "出差行程汇总"
    ws[f"A{row}"].font = Font(bold=True, size=11, color=dark, name="微软雅黑")
    row += 1
    _write_header(ws, row, ["行程编号", "目的地", "起止日期", "订单数", "金额合计", "摘要"], header_font, header_fill, center, border)
    for trip in trips:
        row += 1
        values = [
            f"Trip #{trip['trip_id']}",
            trip["destination"],
            f"{trip['start_date']} ~ {trip['end_date']}",
            len(trip["records"]),
            trip["total"],
            trip["summary"],
        ]
        _write_row(ws, row, values, body_font, center, border)

    row += 2
    ws.merge_cells(f"A{row}:F{row}")
    ws[f"A{row}"] = "按类别汇总"
    ws[f"A{row}"].font = Font(bold=True, size=11, color=dark, name="微软雅黑")
    row += 1
    _write_header(ws, row, ["类别", "笔数", "金额(元)", "占比", "", ""], header_font, header_fill, center, border)
    for category, amount in _category_totals(records):
        row += 1
        count = sum(1 for record in records if record["分类"] == category)
        pct = f"{amount / total * 100:.1f}%" if total else "0.0%"
        _write_row(ws, row, [category, count, amount, pct, "", ""], body_font, center, border)
    row += 1
    _write_row(ws, row, ["合计", len(records), total, "100%", "", ""], Font(bold=True, color=blue, size=11, name="微软雅黑"), center, border)

    for col, width in enumerate([12, 12, 16, 12, 14, 34], 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    ws2 = wb.create_sheet("费用明细")
    ws2.merge_cells("A1:H1")
    ws2["A1"] = "差旅费用明细表"
    ws2["A1"].font = title_font
    headers = ["序号", "日期", "类别", "供应商/平台", "金额(元)", "出发地→目的地", "方法", "附件"]
    _write_header(ws2, 2, headers, header_font, header_fill, center, border)
    for index, record in enumerate(sorted(records, key=lambda item: item["日期"]), 1):
        route = f"{record.get('出发地', '')}→{record.get('目的地', '')}" if record.get("出发地") else "-"
        values = [
            index,
            record["日期"],
            record["分类"],
            record.get("平台") or record.get("供应商") or "-",
            record["金额"],
            route,
            record["方法"],
            record.get("附件") or "-",
        ]
        _write_row(ws2, index + 2, values, body_font, left, border)
    for col, width in enumerate([6, 14, 10, 18, 12, 20, 12, 28], 1):
        ws2.column_dimensions[get_column_letter(col)].width = width

    ws3 = wb.create_sheet("按供应商")
    ws3.merge_cells("A1:D1")
    ws3["A1"] = "按供应商/平台统计"
    ws3["A1"].font = title_font
    _write_header(ws3, 2, ["供应商", "笔数", "金额(元)", "占比"], header_font, header_fill, center, border)
    for index, (vendor, amount, count) in enumerate(_vendor_totals(records), 1):
        pct = f"{amount / total * 100:.1f}%" if total else "0.0%"
        _write_row(ws3, index + 2, [vendor, count, amount, pct], body_font, center, border)
    for col, width in enumerate([20, 10, 14, 10], 1):
        ws3.column_dimensions[get_column_letter(col)].width = width

    report_path = output_dir / f"差旅汇总_demo_{datetime.now().strftime('%Y%m%d')}.xlsx"
    wb.save(report_path)

    print("Demo report generated.")
    print(f"Records: {len(records)}")
    print(f"Total: ¥{total:,.2f}")
    print(f"Excel: {report_path}")
    return 0


def check():
    """Check local readiness without contacting email servers."""
    ok = True
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 8):
        print("FAIL: Python 3.8+ is required.")
        ok = False

    for module_name, package_name, required in [
        ("dotenv", "python-dotenv", True),
        ("PyPDF2", "PyPDF2", True),
        ("openpyxl", "openpyxl", True),
        ("openai", "openai", False),
    ]:
        available = importlib.util.find_spec(module_name) is not None
        status = "OK" if available else ("MISSING" if required else "OPTIONAL")
        print(f"{package_name}: {status}")
        if required and not available:
            ok = False

    env_path = PROJECT_DIR / ".env"
    if env_path.exists():
        print(".env: found")
    else:
        print(".env: not found; run `biztrip init` before scanning email.")

    return 0 if ok else 1


def init_config():
    """Create a starter .env file without reading any secrets."""
    env_path = PROJECT_DIR / ".env"
    example_path = PROJECT_DIR / ".env.example"
    if env_path.exists():
        print(f".env already exists: {env_path}")
        return 0
    if not example_path.exists():
        print(f"Missing template: {example_path}")
        return 1
    shutil.copyfile(example_path, env_path)
    print(f"Created: {env_path}")
    print("Edit EMAIL_ACCOUNT and EMAIL_PASSWORD before running `biztrip scan`.")
    return 0


def scan(args):
    """Run the scanner, interactively by default or non-interactively with options."""
    if args.count < 1:
        print("--count must be greater than 0.")
        return 2
    for label, value in [("--start", args.start), ("--end", args.end)]:
        if value and not _is_date(value):
            print(f"{label} must use YYYY-MM-DD format.")
            return 2

    try:
        from phase2.agent_report import main as agent_main
    except ImportError as exc:
        print(f"Unable to load scanner: {exc}")
        return 1
    interactive = not any([args.start, args.end, args.count != 60, args.no_llm, args.output_dir != str(OUTPUT_DIR)])
    agent_main(
        start=args.start,
        end=args.end,
        count=args.count,
        no_llm=args.no_llm,
        output_dir=args.output_dir,
        interactive=interactive,
    )
    return 0


def _is_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _write_header(ws, row, headers, font, fill, alignment, border):
    for col, value in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = font
        cell.fill = fill
        cell.alignment = alignment
        cell.border = border


def _write_row(ws, row, values, font, alignment, border):
    for col, value in enumerate(values, 1):
        cell = ws.cell(row=row, column=col, value=value)
        cell.font = font
        cell.alignment = alignment
        cell.border = border


def _demo_records():
    return [
        {
            "分类": "机票",
            "平台": "去哪儿网",
            "金额": 1280.0,
            "日期": "2026-07-10",
            "出发地": "上海",
            "目的地": "深圳",
            "方法": "Demo",
            "附件": "demo_flight_invoice.pdf",
        },
        {
            "分类": "酒店",
            "平台": "华住酒店",
            "金额": 598.0,
            "日期": "2026-07-10",
            "目的地": "深圳",
            "方法": "Demo",
            "附件": "demo_hotel_invoice.pdf",
        },
        {
            "分类": "网约车",
            "平台": "滴滴出行",
            "金额": 86.5,
            "日期": "2026-07-10",
            "出发地": "深圳宝安机场",
            "目的地": "南山区酒店",
            "方法": "Demo",
            "附件": "demo_taxi_1.pdf",
        },
        {
            "分类": "网约车",
            "平台": "高德打车",
            "金额": 52.0,
            "日期": "2026-07-11",
            "出发地": "南山区酒店",
            "目的地": "客户办公室",
            "方法": "Demo",
            "附件": "demo_taxi_2.pdf",
        },
        {
            "分类": "发票",
            "平台": "智慧发票",
            "金额": 136.0,
            "日期": "2026-07-11",
            "供应商": "深圳示例餐饮有限公司",
            "方法": "Demo",
            "附件": "demo_meal_invoice.pdf",
        },
    ]


def _demo_trips(records):
    total = sum(record["金额"] for record in records)
    return [
        {
            "trip_id": 1,
            "destination": "深圳",
            "start_date": "2026-07-10",
            "end_date": "2026-07-11",
            "total": total,
            "summary": "上海到深圳客户拜访，含机票、酒店、打车和餐饮发票。",
            "records": records,
        }
    ]


def _category_totals(records):
    totals = {}
    for record in records:
        totals[record["分类"]] = totals.get(record["分类"], 0) + record["金额"]
    return sorted(totals.items(), key=lambda item: -item[1])


def _vendor_totals(records):
    totals = {}
    for record in records:
        vendor = record.get("供应商") or record.get("平台") or "其他"
        if vendor not in totals:
            totals[vendor] = {"count": 0, "amount": 0}
        totals[vendor]["count"] += 1
        totals[vendor]["amount"] += record["金额"]
    return [
        (vendor, data["amount"], data["count"])
        for vendor, data in sorted(totals.items(), key=lambda item: -item[1]["amount"])
    ]


if __name__ == "__main__":
    raise SystemExit(main())
