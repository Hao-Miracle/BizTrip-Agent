"""Local web interface for BizTrip Agent."""

import argparse
import html
import importlib.util
import shutil
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


def run_server(host="127.0.0.1", port=8765, open_browser=True):
    """Start the local web UI and block until interrupted."""
    server = ThreadingHTTPServer((host, port), BizTripWebHandler)
    url = f"http://{host}:{server.server_port}/"
    print(f"BizTrip Agent web is running: {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping BizTrip Agent web.")
    finally:
        server.server_close()
    return 0


class BizTripWebHandler(BaseHTTPRequestHandler):
    """Small local-only HTTP handler for safe report generation flows."""

    server_version = "BizTripAgentWeb/0.1"

    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            self._send_html(render_home())
            return
        self.send_error(404)

    def do_HEAD(self):
        if self.path in {"/", "/index.html"}:
            self._send_headers(len(render_home().encode("utf-8")))
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = {key: values[-1] for key, values in parse_qs(body).items()}
        if self.path == "/demo":
            self._send_html(_run_demo(form))
            return
        if self.path == "/rebuild":
            self._send_html(_run_rebuild(form))
            return
        if self.path == "/init":
            self._send_html(_run_init())
            return
        self.send_error(404)

    def log_message(self, format, *args):
        return

    def _send_html(self, body, status=200):
        data = body.encode("utf-8")
        self._send_headers(len(data), status=status)
        self.wfile.write(data)

    def _send_headers(self, length, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()


def render_home(message=None, error=None, files=None):
    """Render the local web UI."""
    message_html = ""
    if message:
        message_html = f'<div class="notice ok">{html.escape(message)}</div>'
    if error:
        message_html = f'<div class="notice bad">{html.escape(error)}</div>'
    files_html = _files_html(files or [])
    readiness_html = _readiness_html(readiness_status())
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizTrip Agent</title>
  <style>
    :root {{
      --text: #202124;
      --muted: #5f6368;
      --line: #dadce0;
      --panel: #ffffff;
      --soft: #f8fafd;
      --blue: #0b57d0;
      --green: #137333;
      --red: #b3261e;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      color: var(--text);
      background: var(--soft);
    }}
    header {{
      padding: 22px 28px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{ margin: 0; font-size: 22px; }}
    .sub {{ margin-top: 6px; color: var(--muted); font-size: 13px; }}
    main {{
      display: grid;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
      gap: 18px;
      padding: 22px 28px 32px;
      max-width: 1120px;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 18px;
    }}
    h2 {{ margin: 0 0 12px; font-size: 17px; }}
    label {{ display: block; margin: 12px 0 6px; font-size: 13px; color: var(--muted); }}
    input[type="text"] {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      padding: 8px 10px;
      font: inherit;
      background: #fff;
    }}
    .check {{ display: flex; align-items: center; gap: 8px; margin-top: 12px; color: var(--text); }}
    button {{
      margin-top: 16px;
      min-height: 38px;
      border: 1px solid var(--blue);
      background: var(--blue);
      color: #fff;
      padding: 8px 14px;
      font: inherit;
      font-weight: 650;
      cursor: pointer;
    }}
    .notice {{
      grid-column: 1 / -1;
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 12px 14px;
      font-size: 14px;
    }}
    .ok {{ border-color: #a8dab5; color: var(--green); }}
    .bad {{ border-color: #f4b6b1; color: var(--red); }}
    .files {{
      grid-column: 1 / -1;
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 14px 18px;
    }}
    .files ul {{ margin: 8px 0 0; padding-left: 20px; }}
    .files li {{ margin: 4px 0; overflow-wrap: anywhere; }}
    .readiness {{
      grid-column: 1 / -1;
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px 18px;
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .status {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      min-height: 66px;
      background: #fff;
    }}
    .status strong {{ display: block; font-size: 14px; }}
    .status span {{ display: block; margin-top: 4px; color: var(--muted); font-size: 13px; }}
    .status.ok {{ border-color: #a8dab5; }}
    .status.warn {{ border-color: #fdd663; }}
    .status.bad {{ border-color: #f4b6b1; }}
    .secondary {{
      border-color: var(--line);
      background: #fff;
      color: var(--text);
    }}
    @media (max-width: 760px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      main {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>BizTrip Agent</h1>
    <div class="sub">本地报表工作台，只处理你电脑上的文件。</div>
  </header>
  <main>
    {message_html}
    {files_html}
    {readiness_html}
    <section>
      <h2>生成 Demo</h2>
      <form method="post" action="/demo">
        <label for="demo-output">输出目录</label>
        <input id="demo-output" name="output_dir" type="text" value="output">
        <label class="check"><input name="review" type="checkbox" checked> 同时生成审阅页面</label>
        <button type="submit">生成 Demo</button>
      </form>
    </section>
    <section>
      <h2>从 JSON 重建</h2>
      <form method="post" action="/rebuild">
        <label for="json-path">records_YYYYMMDD.json 路径</label>
        <input id="json-path" name="json_path" type="text" placeholder="output/records_20260729.json">
        <label for="rebuild-output">输出目录</label>
        <input id="rebuild-output" name="output_dir" type="text" placeholder="留空则输出到 JSON 所在目录">
        <label class="check"><input name="review" type="checkbox" checked> 同时生成审阅页面</label>
        <button type="submit">重建报表</button>
      </form>
    </section>
  </main>
</body>
</html>
"""


def readiness_status(project_dir=None):
    """Return local readiness flags without exposing secret values."""
    project_dir = Path(project_dir) if project_dir else Path(__file__).resolve().parents[1]
    env_path = project_dir / ".env"
    env_values = _read_env_flags(env_path)
    return [
        {
            "label": "Python",
            "state": "ok" if sys.version_info >= (3, 8) else "bad",
            "detail": f"{sys.version.split()[0]}，需要 3.8+",
        },
        *_dependency_status(),
        {
            "label": ".env 文件",
            "state": "ok" if env_path.exists() else "warn",
            "detail": "已创建" if env_path.exists() else "未创建，可先生成模板",
        },
        {
            "label": "邮箱账号",
            "state": "ok" if env_values.get("EMAIL_ACCOUNT") else "warn",
            "detail": "已填写" if env_values.get("EMAIL_ACCOUNT") else "未填写",
        },
        {
            "label": "邮箱授权码",
            "state": "ok" if env_values.get("EMAIL_PASSWORD") else "warn",
            "detail": "已填写" if env_values.get("EMAIL_PASSWORD") else "未填写",
        },
        {
            "label": "LLM 增强",
            "state": "ok" if env_values.get("LLM_API_KEY") else "warn",
            "detail": "已启用" if env_values.get("LLM_API_KEY") else "未启用，将使用规则模式",
        },
    ]


def _dependency_status():
    packages = [
        ("python-dotenv", "dotenv", True),
        ("PyPDF2", "PyPDF2", True),
        ("openpyxl", "openpyxl", True),
        ("openai", "openai", False),
    ]
    rows = []
    for package_name, module_name, required in packages:
        available = importlib.util.find_spec(module_name) is not None
        if available:
            state = "ok"
            detail = "已安装"
        elif required:
            state = "bad"
            detail = "缺失，运行 pip install -e ."
        else:
            state = "warn"
            detail = "未安装，可选"
        rows.append({"label": package_name, "state": state, "detail": detail})
    return rows


def _read_env_flags(env_path):
    if not env_path.exists():
        return {}
    flags = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        flags[key.strip()] = bool(value.strip().strip("\"'"))
    return flags


def _run_demo(form):
    from biztrip_agent.cli import OUTPUT_DIR, demo

    output_dir = Path(form.get("output_dir") or OUTPUT_DIR)
    review = form.get("review") == "on"
    exit_code = demo(output_dir, review=review)
    if exit_code != 0:
        return render_home(error="Demo 生成失败，请回到终端查看错误信息。")
    return render_home(message="Demo 已生成。", files=_latest_files(output_dir))


def _run_rebuild(form):
    from biztrip_agent.cli import rebuild

    json_path = form.get("json_path", "").strip()
    if not json_path:
        return render_home(error="请选择 records_YYYYMMDD.json 文件路径。")
    output_dir = form.get("output_dir", "").strip()
    args = argparse.Namespace(json_path=json_path, output_dir=output_dir or None, review=form.get("review") == "on")
    exit_code = rebuild(args)
    if exit_code != 0:
        return render_home(error="重建失败，请确认 JSON 路径正确。")
    target_dir = Path(output_dir) if output_dir else Path(json_path).parent
    return render_home(message="报表已重建。", files=_latest_files(target_dir))


def _run_init():
    project_dir = Path(__file__).resolve().parents[1]
    env_path = project_dir / ".env"
    example_path = project_dir / ".env.example"
    if env_path.exists():
        return render_home(message=".env 已存在，不会覆盖现有配置。")
    if not example_path.exists():
        return render_home(error="未找到 .env.example，无法生成模板。")
    shutil.copyfile(example_path, env_path)
    return render_home(message=".env 模板已创建。请在本地编辑邮箱账号和授权码。")


def _latest_files(output_dir):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return []
    names = ["*.xlsx", "review_*.html", "records_*.json"]
    files = []
    for pattern in names:
        files.extend(output_dir.glob(pattern))
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:6]


def _files_html(files):
    if not files:
        return ""
    rows = "".join(f"<li>{html.escape(str(path))}</li>" for path in files)
    return f'<section class="files"><h2>生成文件</h2><ul>{rows}</ul></section>'


def _readiness_html(statuses):
    rows = []
    for item in statuses:
        rows.append(
            f'<div class="status {html.escape(item["state"])}">'
            f'<strong>{html.escape(item["label"])}</strong>'
            f'<span>{html.escape(item["detail"])}</span>'
            "</div>"
        )
    return (
        '<section class="readiness">'
        "<h2>本地就绪检查</h2>"
        '<div class="sub">只显示是否已配置，不显示邮箱授权码或 API Key。</div>'
        f'<div class="status-grid">{"".join(rows)}</div>'
        '<form method="post" action="/init">'
        '<button class="secondary" type="submit">生成 .env 模板</button>'
        "</form>"
        "</section>"
    )
