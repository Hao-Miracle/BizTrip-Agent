#!/usr/bin/env python3
"""Self-contained, read-only mailbox audit bundled with the public Skill."""

import argparse
import email
import html
import imaplib
import json
import os
import re
import stat
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs


SCHEMA = "biztrip.skill-audit.v1"
MAX_MESSAGES = 60
MAX_DAYS = 31
MAX_RECORDS = 20
MAX_BODY_CHARS = 1200

DOMAIN_RULES = {
    "机票": ["qunar", "ctrip", "fliggy", "alitrip", "airchina", "ceair", "csair", "trip.com"],
    "火车票": ["12306", "zhixing", "tiexing"],
    "酒店": ["booking", "agoda", "airbnb", "meituan", "elong", "huazhu", "hotel"],
    "网约车": ["didi", "xiaojukeji", "uber", "gaode", "amap", "shouqi"],
    "发票": ["fapiao", "invoice", "crestv", "txffp"],
}
KEYWORD_RULES = {
    "机票": ["机票", "航班", "登机", "航空", "flight", "boarding"],
    "火车票": ["火车票", "高铁", "动车", "12306", "车票", "train"],
    "酒店": ["酒店", "民宿", "入住", "住宿", "hotel", "booking confirmation"],
    "网约车": ["滴滴", "网约车", "快车", "专车", "出租车", "行程单"],
    "发票": ["发票", "invoice", "电子凭证", "receipt"],
}
AMOUNT_PATTERNS = [
    re.compile(r"(?:价税合计|支付金额|实付金额|订单金额|合计|金额)[：:\s]*[¥￥]?\s*([0-9]+(?:\.[0-9]{1,2})?)\s*元?", re.I),
    re.compile(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)"),
    re.compile(r"([0-9]+(?:\.[0-9]{1,2})?)\s*元"),
]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["status", "setup", "audit"])
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)
    config_path = Path(args.config).expanduser()

    if args.command == "status":
        configured = bool(load_config(config_path))
        emit(configured, "ready" if configured else "setup_required")
        return 0 if configured else 1
    if args.command == "setup":
        return setup(config_path, args.port)
    error = range_error(args.start, args.end, args.count)
    if error:
        emit(False, "failed", error={"code": "invalid_range", "message": error})
        return 1
    config = load_config(config_path)
    if not config:
        emit(False, "setup_required", next_action="run_setup")
        return 1
    try:
        records, scan_label = audit_mailbox(config, args.start, args.end, args.count)
    except imaplib.IMAP4.error:
        emit(False, "failed", error={"code": "mail_login_failed", "message": "邮箱连接失败，请重新运行本地邮箱设置。"})
        return 1
    except Exception as exc:
        emit(False, "failed", error={"code": "mailbox_error", "message": safe_error(exc)})
        return 1
    emit(True, "audit_ready", **audit_result(records, scan_label))
    return 0


def default_config_path():
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config")
    return root / "biztrip-agent" / "skill-email.json"


def load_config(path):
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    required = ("account", "password", "server", "port")
    return payload if all(payload.get(key) for key in required) else None


def save_config(path, config):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def setup(config_path, port):
    state = {"saved": False}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.render()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            values = parse_qs(self.rfile.read(length).decode("utf-8"))
            account = first(values, "account").strip()
            password = first(values, "password").strip()
            server = first(values, "server").strip() or infer_server(account)
            try:
                port_value = int(first(values, "port") or "993")
                test_mailbox(account, password, server, port_value)
                save_config(config_path, {"account": account, "password": password, "server": server, "port": port_value})
            except Exception:
                self.render("连接失败。请确认已开启 IMAP，并填写邮箱授权码或应用专用密码。")
                return
            state["saved"] = True
            self.render("邮箱已保存，可以关闭此页面并返回 Agent。", success=True)

        def render(self, message="", success=False):
            current = load_config(config_path) or {}
            notice = f'<p class="notice {"ok" if success else "bad"}">{html.escape(message)}</p>' if message else ""
            disabled = " disabled" if success else ""
            body = f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BizTrip 邮箱设置</title><style>body{{font-family:system-ui;max-width:680px;margin:48px auto;padding:0 20px;color:#202124}}label{{display:block;margin-top:18px}}input{{box-sizing:border-box;width:100%;padding:12px;margin-top:6px}}button{{margin-top:24px;padding:12px 20px;background:#2457d6;color:white;border:0}}.sub{{color:#5f6368;line-height:1.6}}.notice{{padding:12px;border:1px solid}}.ok{{color:#137333}}.bad{{color:#b3261e}}</style>
<h1>连接差旅邮箱</h1><p class="sub">仅用于只读体检。请填写邮箱授权码或应用专用密码，不要填写网页登录密码。配置只保存在这台电脑。</p>{notice}
<form method="post"><label>邮箱账号<input name="account" value="{html.escape(current.get('account', ''))}" required{disabled}></label><label>邮箱授权码<input name="password" type="password" required{disabled}></label><label>IMAP 服务器（通常留空）<input name="server" placeholder="自动识别"{disabled}></label><input name="port" type="hidden" value="993"><button{disabled}>验证并保存</button></form>
<p class="sub">QQ、163、126：先在邮箱设置中开启 IMAP 并生成授权码。Gmail、Outlook：使用应用专用密码；企业邮箱可填写管理员提供的 IMAP 地址。</p></html>"""
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, _format, *_args):
            return

    server = HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    threading.Timer(0.2, lambda: webbrowser.open(url)).start()
    print(json.dumps({"schema_version": SCHEMA, "status": "setup_open", "url": url}, ensure_ascii=False), flush=True)
    while not state["saved"]:
        server.handle_request()
    server.server_close()
    return 0


def test_mailbox(account, password, server, port):
    if not account or not password or not server:
        raise ValueError("missing mailbox configuration")
    conn = imaplib.IMAP4_SSL(server, port)
    try:
        conn.login(account, password)
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def audit_mailbox(config, start=None, end=None, count=60):
    conn = imaplib.IMAP4_SSL(config["server"], int(config["port"]))
    try:
        conn.login(config["account"], config["password"])
        conn.select("INBOX", readonly=True)
        if start:
            after = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
            search_args = ("SINCE", imap_date(start), "BEFORE", after.strftime("%d-%b-%Y"))
            scan_label = f"{start} 至 {end}"
        else:
            search_args = ("ALL",)
            scan_label = f"最近 {count} 封邮件"
        status, data = conn.search(None, *search_args)
        if status != "OK":
            raise RuntimeError("邮箱搜索失败。")
        ids = data[0].split()
        ids = ids[-count:] if not start else ids[-500:]
        records = []
        for message_id in reversed(ids):
            status, content = conn.fetch(message_id, "(RFC822)")
            if status != "OK" or not content or not isinstance(content[0], tuple):
                continue
            item = public_record(email.message_from_bytes(content[0][1]))
            if item:
                records.append(item)
    finally:
        try:
            conn.logout()
        except Exception:
            pass
    return records, scan_label


def public_record(message):
    subject = decode_text(message.get("Subject"))
    sender = decode_text(message.get("From"))
    body = message_body(message)
    category = classify(sender, subject, body)
    if not category:
        return None
    attachments = attachment_names(message)
    amounts = extract_amounts(f"{subject}\n{body}")
    date = ""
    try:
        date = parsedate_to_datetime(message.get("Date")).date().isoformat()
    except Exception:
        pass
    issues = []
    if not amounts:
        issues.append("missing_amount")
    if not attachments:
        issues.append("no_attachment_detected")
    return {
        "category": category,
        "date": date,
        "vendor_hint": sender[:160],
        "subject": subject[:240],
        "amount_candidates": amounts[:5],
        "attachment_names": attachments[:10],
        "body_excerpt": compact(body)[:MAX_BODY_CHARS],
        "issue_codes": issues,
    }


def audit_result(records, scan_label):
    categories = {}
    amount_total = 0.0
    amount_known = 0
    issue_count = 0
    for record in records:
        bucket = categories.setdefault(record["category"], {"count": 0, "candidate_amount": 0.0})
        bucket["count"] += 1
        if record["amount_candidates"]:
            amount = record["amount_candidates"][0]
            bucket["candidate_amount"] += amount
            amount_total += amount
            amount_known += 1
        issue_count += len(record["issue_codes"])
    return {
        "scan_label": scan_label,
        "summary": {
            "candidate_record_count": len(records),
            "amount_known_count": amount_known,
            "candidate_total": round(amount_total, 2),
            "issue_count": issue_count,
        },
        "categories": categories,
        "records": records[:MAX_RECORDS],
        "records_truncated": len(records) > MAX_RECORDS,
        "files": {"excel": "", "package_dir": ""},
        "next_action": "present_audit",
        "full_package": {"requires": "local_personal_app"},
    }


def classify(sender, subject, body):
    sender_lower = sender.lower()
    for category, values in DOMAIN_RULES.items():
        if any(value in sender_lower for value in values):
            return category
    text = f"{subject}\n{body[:2000]}".lower()
    for category, values in KEYWORD_RULES.items():
        if any(value in text for value in values):
            return category
    return None


def message_body(message):
    parts = message.walk() if message.is_multipart() else [message]
    plain = ""
    html_body = ""
    for part in parts:
        if part.get_content_disposition() == "attachment":
            continue
        content_type = part.get_content_type()
        if content_type not in {"text/plain", "text/html"}:
            continue
        raw = part.get_payload(decode=True)
        if not raw:
            continue
        text = decode_bytes(raw, part.get_content_charset())
        if content_type == "text/plain" and not plain:
            plain = text
        elif content_type == "text/html" and not html_body:
            html_body = re.sub(r"<[^>]+>", " ", text)
    return plain or html_body


def attachment_names(message):
    names = []
    for part in message.walk() if message.is_multipart() else []:
        filename = part.get_filename()
        if filename:
            names.append(decode_text(filename))
    return names


def extract_amounts(text):
    values = []
    for pattern in AMOUNT_PATTERNS:
        for match in pattern.findall(text):
            try:
                value = round(float(match), 2)
            except ValueError:
                continue
            if 0 < value < 1000000 and value not in values:
                values.append(value)
    return values


def decode_text(value):
    result = []
    for content, charset in decode_header(value or ""):
        result.append(decode_bytes(content, charset) if isinstance(content, bytes) else content)
    return "".join(result)


def decode_bytes(value, charset=None):
    for encoding in [charset, "utf-8", "gb18030", "latin1"]:
        if not encoding:
            continue
        try:
            return value.decode(encoding, errors="replace")
        except (LookupError, UnicodeDecodeError):
            pass
    return value.decode("utf-8", errors="replace")


def infer_server(account):
    domain = account.rsplit("@", 1)[-1].lower()
    return {
        "qq.com": "imap.qq.com",
        "163.com": "imap.163.com",
        "126.com": "imap.126.com",
        "gmail.com": "imap.gmail.com",
        "outlook.com": "outlook.office365.com",
        "hotmail.com": "outlook.office365.com",
    }.get(domain, "")


def range_error(start, end, count):
    if count < 1 or count > MAX_MESSAGES:
        return "体检最多读取最近 60 封邮件。"
    if bool(start) != bool(end):
        return "按日期体检时必须同时提供开始和结束日期。"
    if not start:
        return ""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        return "日期必须使用 YYYY-MM-DD 格式。"
    if end_date < start_date:
        return "结束日期不能早于开始日期。"
    if (end_date - start_date).days >= MAX_DAYS:
        return "Skill 体检最多覆盖连续 31 天。"
    return ""


def imap_date(value):
    return datetime.strptime(value, "%Y-%m-%d").strftime("%d-%b-%Y")


def first(values, key):
    return (values.get(key) or [""])[0]


def compact(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def safe_error(exc):
    text = str(exc).strip()
    return text[:300] if text else exc.__class__.__name__


def emit(ok, status, **extra):
    payload = {"schema_version": SCHEMA, "ok": ok, "status": status}
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
