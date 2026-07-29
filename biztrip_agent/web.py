"""Local web interface for BizTrip Agent."""

import argparse
import html
import importlib.util
import json
import shutil
import sys
import threading
import time
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


JOBS = {}
JOBS_LOCK = threading.Lock()
MAX_JOBS = 20


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
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_html(render_home())
            return
        if parsed.path.startswith("/jobs/"):
            self._send_json(_job_snapshot(parsed.path.rsplit("/", 1)[-1]))
            return
        self.send_error(404)

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
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
        if self.path == "/scan":
            self._send_json(_run_scan(form))
            return
        if self.path == "/init":
            self._send_html(_run_init())
            return
        if self.path == "/config":
            self._send_html(_run_config(form))
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

    def _send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def render_home(message=None, error=None, files=None, result_summary=None):
    """Render the local web UI."""
    message_html = ""
    if message:
        message_html = f'<div class="notice ok">{html.escape(message)}</div>'
    if error:
        message_html = f'<div class="notice bad">{html.escape(error)}</div>'
    files_html = _files_html(files or [])
    readiness_html = _readiness_html(readiness_status())
    config_html = _config_html()
    recent_html = _recent_results_html()
    summary_html = _summary_html(result_summary)
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
    input[type="number"] {{
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
    .results {{
      grid-column: 1 / -1;
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px 18px;
    }}
    .result-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(150px, 1fr));
      gap: 10px;
      margin-top: 10px;
    }}
    .result-metric {{
      border: 1px solid var(--line);
      padding: 10px 12px;
      background: #fff;
    }}
    .result-metric strong {{ display: block; font-size: 18px; }}
    .result-metric span {{ display: block; margin-top: 3px; color: var(--muted); font-size: 13px; }}
    .job {{
      grid-column: 1 / -1;
      display: none;
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 14px 18px;
    }}
    .job.active {{ display: block; }}
    .job-state {{ font-weight: 700; }}
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
    .config {{
      grid-column: 1 / -1;
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px 18px;
    }}
    .config-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 12px;
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
    {summary_html}
    {recent_html}
    <section id="job-panel" class="job">
      <h2>任务进度</h2>
      <div id="job-state" class="job-state">等待提交</div>
      <div id="job-detail" class="sub"></div>
      <div id="job-files"></div>
    </section>
    {readiness_html}
    {config_html}
    <section>
      <h2>扫描邮箱</h2>
      <form method="post" action="/scan" data-background="true">
        <label for="scan-start">开始日期</label>
        <input id="scan-start" name="start" type="text" placeholder="YYYY-MM-DD，可留空">
        <label for="scan-end">结束日期</label>
        <input id="scan-end" name="end" type="text" placeholder="YYYY-MM-DD，可留空">
        <label for="scan-count">扫描邮件数量</label>
        <input id="scan-count" name="count" type="number" min="1" value="60">
        <label for="scan-output">输出目录</label>
        <input id="scan-output" name="output_dir" type="text" value="output">
        <label class="check"><input name="review" type="checkbox" checked> 同时生成审阅页面</label>
        <label class="check"><input name="no_llm" type="checkbox"> 只用规则模式</label>
        <button type="submit">开始扫描</button>
      </form>
    </section>
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
  <script>
    const jobPanel = document.getElementById("job-panel");
    const jobState = document.getElementById("job-state");
    const jobDetail = document.getElementById("job-detail");
    const jobFiles = document.getElementById("job-files");
    document.querySelectorAll("form[data-background='true']").forEach((form) => {{
      form.addEventListener("submit", async (event) => {{
        event.preventDefault();
        jobPanel.classList.add("active");
        jobState.textContent = "正在提交";
        jobDetail.textContent = "";
        jobFiles.innerHTML = "";
        const response = await fetch(form.action, {{ method: "POST", body: new URLSearchParams(new FormData(form)) }});
        if (!response.ok) {{
          jobState.textContent = "提交失败";
          jobDetail.textContent = "请检查输入后重试。";
          return;
        }}
        const payload = await response.json();
        if (payload.error) {{
          jobState.textContent = "无法开始";
          jobDetail.textContent = payload.error;
          return;
        }}
        pollJob(payload.job_id);
      }});
    }});
    async function pollJob(jobId) {{
      const response = await fetch(`/jobs/${{jobId}}`);
      const job = await response.json();
      jobState.textContent = job.label;
      jobDetail.textContent = job.message || "";
      if (job.files && job.files.length) {{
        jobFiles.innerHTML = "<ul>" + job.files.map((file) => `<li>${{escapeHtml(file)}}</li>`).join("") + "</ul>";
      }}
      if (job.status === "queued" || job.status === "running") {{
        setTimeout(() => pollJob(jobId), 1200);
      }}
    }}
    function escapeHtml(value) {{
      return value.replace(/[&<>"']/g, (char) => ({{"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}}[char]));
    }}
  </script>
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


def _env_path():
    return Path(__file__).resolve().parents[1] / ".env"


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


def _read_env_values(env_path):
    if not env_path.exists():
        return {}
    values = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _write_env_values(env_path, updates):
    env_path = Path(env_path)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen = set()
    lines = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(line)
            continue
        key, _value = stripped.split("=", 1)
        key = key.strip()
        if key in updates:
            lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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


def _run_scan(form):
    from biztrip_agent.cli import OUTPUT_DIR

    start = form.get("start", "").strip() or None
    end = form.get("end", "").strip() or None
    count_value = form.get("count", "").strip() or "60"
    output_dir = form.get("output_dir", "").strip() or str(OUTPUT_DIR)
    error = _validate_scan_inputs(start, end, count_value)
    if error:
        return {"error": error}

    preflight_error = _preflight_scan(output_dir)
    if preflight_error:
        return {"error": preflight_error}

    args = argparse.Namespace(
        start=start,
        end=end,
        count=int(count_value),
        no_llm=form.get("no_llm") == "on",
        review=form.get("review") == "on",
        output_dir=output_dir,
    )
    job_id = _start_job("扫描邮箱", _scan_job, args, output_dir)
    return {"job_id": job_id}


def _scan_job(args, output_dir):
    from biztrip_agent.cli import scan

    exit_code = scan(args)
    if exit_code != 0:
        raise RuntimeError("扫描失败，请检查邮箱授权码、IMAP 设置、网络连接和终端错误信息。")
    return {
        "message": "扫描完成。",
        "files": [str(path) for path in _latest_files(output_dir)],
        "summary": _result_summary(output_dir),
    }


def _start_job(name, target, *args):
    job_id = uuid.uuid4().hex[:12]
    now = time.time()
    job = {
        "id": job_id,
        "name": name,
        "status": "queued",
        "label": "排队中",
        "message": "任务已提交，等待开始。",
        "files": [],
        "summary": None,
        "created_at": now,
        "updated_at": now,
    }
    with JOBS_LOCK:
        _trim_jobs()
        JOBS[job_id] = job
    thread = threading.Thread(target=_run_job, args=(job_id, target, args), daemon=True)
    thread.start()
    return job_id


def _run_job(job_id, target, args):
    _update_job(job_id, status="running", label="运行中", message="正在处理，请保持此页面打开。")
    try:
        result = target(*args)
    except Exception as exc:
        _update_job(
            job_id,
            status="failed",
            label="失败",
            message=_friendly_error(exc),
            traceback=traceback.format_exc(),
        )
        return
    _update_job(
        job_id,
        status="succeeded",
        label="完成",
        message=result.get("message", "任务完成。"),
        files=result.get("files", []),
        summary=result.get("summary"),
    )


def _update_job(job_id, **updates):
    updates["updated_at"] = time.time()
    with JOBS_LOCK:
        if job_id in JOBS:
            JOBS[job_id].update(updates)


def _job_snapshot(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return {"status": "missing", "label": "未找到任务", "message": "任务不存在或已过期。", "files": []}
        return {key: value for key, value in job.items() if key != "traceback"}


def _trim_jobs():
    if len(JOBS) < MAX_JOBS:
        return
    oldest = sorted(JOBS.items(), key=lambda item: item[1].get("updated_at", 0))
    for job_id, _job in oldest[: len(JOBS) - MAX_JOBS + 1]:
        JOBS.pop(job_id, None)


def _preflight_scan(output_dir):
    env_flags = _read_env_flags(_env_path())
    if not env_flags.get("EMAIL_ACCOUNT"):
        return "请先在 .env 中填写 EMAIL_ACCOUNT。"
    if not env_flags.get("EMAIL_PASSWORD"):
        return "请先在 .env 中填写邮箱授权码 EMAIL_PASSWORD。"
    output_path = Path(output_dir)
    try:
        output_path.mkdir(parents=True, exist_ok=True)
        probe = output_path / ".biztrip_write_check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return "输出目录不可写，请换一个目录。"
    return None


def _friendly_error(exc):
    text = str(exc)
    lowered = text.lower()
    if "help.mail.qq.com/detail/108/1023" in lowered or "account is abnormal" in lowered:
        return (
            "QQ 邮箱登录失败：请确认已在 QQ 邮箱设置中开启 IMAP/SMTP 服务，并使用 QQ 邮箱生成的授权码，"
            "不是 QQ 登录密码；如果刚连续失败多次，请等待几分钟后再试。"
        )
    if "authentication" in lowered or "login" in lowered or "password" in lowered:
        return "邮箱登录失败：请确认邮箱授权码正确，并且 IMAP 服务已开启。"
    if "imap" in lowered:
        return "IMAP 连接失败：请确认邮箱服务商、网络和授权码设置。"
    if "network" in lowered or "timed out" in lowered or "timeout" in lowered:
        return "网络连接失败：请检查网络后重试。"
    if "no such file" in lowered or "not found" in lowered:
        return "文件或目录不存在：请检查输出目录和附件路径。"
    return text or "任务失败，请查看终端错误信息。"


def _validate_scan_inputs(start, end, count_value):
    from biztrip_agent.cli import _is_date

    for label, value in [("开始日期", start), ("结束日期", end)]:
        if value and not _is_date(value):
            return f"{label}必须使用 YYYY-MM-DD 格式。"
    try:
        count = int(count_value)
    except ValueError:
        return "扫描邮件数量必须是整数。"
    if count < 1:
        return "扫描邮件数量必须大于 0。"
    return None


def _run_init():
    env_path = _env_path()
    example_path = env_path.parent / ".env.example"
    if env_path.exists():
        return render_home(message=".env 已存在，不会覆盖现有配置。")
    if not example_path.exists():
        return render_home(error="未找到 .env.example，无法生成模板。")
    shutil.copyfile(example_path, env_path)
    return render_home(message=".env 模板已创建。请在本地编辑邮箱账号和授权码。")


def _run_config(form):
    env_path = _env_path()
    updates = {}
    plain_fields = ["EMAIL_ACCOUNT", "IMAP_SERVER", "LLM_BASE_URL", "LLM_MODEL"]
    secret_fields = ["EMAIL_PASSWORD", "LLM_API_KEY"]
    for key in plain_fields:
        value = form.get(key, "").strip()
        updates[key] = value
    for key in secret_fields:
        value = form.get(key, "").strip()
        if value:
            updates[key] = value
    if not updates.get("EMAIL_ACCOUNT"):
        return render_home(error="邮箱账号不能为空。")
    _write_env_values(env_path, updates)
    return render_home(message="配置已保存。密码和 API Key 不会在页面显示。")


def _latest_files(output_dir):
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return []
    names = ["*.xlsx", "review_*.html", "records_*.json"]
    files = []
    for pattern in names:
        files.extend(output_dir.glob(pattern))
    return sorted(files, key=lambda path: path.stat().st_mtime, reverse=True)[:6]


def _result_summary(output_dir):
    records = _latest_records_json(output_dir)
    if not records:
        return None
    try:
        payload = json.loads(records.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    summary = payload.get("summary", {})
    return {
        "record_count": summary.get("record_count", 0),
        "trip_count": summary.get("trip_count", 0),
        "total_amount": summary.get("total_amount", 0),
        "scan_label": payload.get("scan_label") or "最近结果",
        "json_path": str(records),
    }


def _latest_records_json(output_dir=None):
    roots = [Path(output_dir)] if output_dir else [Path("output"), Path(__file__).resolve().parents[1] / "output"]
    files = []
    for root in roots:
        if root.exists():
            files.extend(root.glob("records_*.json"))
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)


def _files_html(files):
    if not files:
        return ""
    rows = "".join(f"<li>{html.escape(str(path))}</li>" for path in files)
    return f'<section class="files"><h2>生成文件</h2><ul>{rows}</ul></section>'


def _summary_html(summary):
    summary = summary or _result_summary("output")
    if not summary:
        return ""
    return (
        '<section class="results">'
        "<h2>最近结果</h2>"
        f'<div class="sub">{html.escape(str(summary.get("scan_label") or "最近结果"))}</div>'
        '<div class="result-grid">'
        f'<div class="result-metric"><strong>¥ {float(summary.get("total_amount") or 0):,.2f}</strong><span>总金额</span></div>'
        f'<div class="result-metric"><strong>{int(summary.get("record_count") or 0)}</strong><span>记录数</span></div>'
        f'<div class="result-metric"><strong>{int(summary.get("trip_count") or 0)}</strong><span>行程数</span></div>'
        "</div>"
        f'<div class="sub">JSON：{html.escape(str(summary.get("json_path") or ""))}</div>'
        "</section>"
    )


def _recent_results_html():
    files = _latest_files("output")
    if not files:
        return ""
    return _files_html(files)


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


def _config_html():
    values = _read_env_values(_env_path())
    return f"""
    <section class="config">
      <h2>邮箱配置</h2>
      <div class="sub">在本机浏览器填写并保存到 .env。授权码和 API Key 留空表示保留原值，页面不会回显。</div>
      <form method="post" action="/config">
        <div class="config-grid">
          <div>
            <label for="cfg-email">邮箱账号</label>
            <input id="cfg-email" name="EMAIL_ACCOUNT" type="text" value="{html.escape(values.get("EMAIL_ACCOUNT", ""))}">
          </div>
          <div>
            <label for="cfg-password">邮箱授权码</label>
            <input id="cfg-password" name="EMAIL_PASSWORD" type="password" placeholder="{_secret_placeholder(values.get("EMAIL_PASSWORD"))}">
          </div>
          <div>
            <label for="cfg-imap">IMAP 服务器</label>
            <input id="cfg-imap" name="IMAP_SERVER" type="text" value="{html.escape(values.get("IMAP_SERVER", ""))}" placeholder="可留空自动推断">
          </div>
          <div>
            <label for="cfg-key">LLM API Key（可选）</label>
            <input id="cfg-key" name="LLM_API_KEY" type="password" placeholder="{_secret_placeholder(values.get("LLM_API_KEY"))}">
          </div>
          <div>
            <label for="cfg-base">LLM Base URL（可选）</label>
            <input id="cfg-base" name="LLM_BASE_URL" type="text" value="{html.escape(values.get("LLM_BASE_URL", ""))}">
          </div>
          <div>
            <label for="cfg-model">LLM Model（可选）</label>
            <input id="cfg-model" name="LLM_MODEL" type="text" value="{html.escape(values.get("LLM_MODEL", ""))}">
          </div>
        </div>
        <button type="submit">保存配置</button>
      </form>
    </section>
"""


def _secret_placeholder(value):
    return "已填写，留空保留" if value else "未填写"
