from datetime import datetime
from http.client import HTTPConnection
from threading import Thread
import time

from http.server import ThreadingHTTPServer

from biztrip_agent.cli import main
from biztrip_agent.web import (
    BizTripWebHandler,
    _friendly_error,
    _job_snapshot,
    _preflight_scan,
    _result_summary,
    _run_demo,
    _run_scan,
    _start_job,
    _validate_scan_inputs,
    readiness_status,
    render_home,
)


def test_web_home_contains_local_workflows():
    html = render_home()

    assert "BizTrip Agent" in html
    assert 'action="/demo"' in html
    assert 'action="/rebuild"' in html
    assert 'action="/scan"' in html
    assert 'action="/init"' in html
    assert "本地就绪检查" in html
    assert "records_YYYYMMDD.json" in html


def test_web_rejects_invalid_port():
    assert main(["web", "--port", "70000"]) == 2


def test_web_demo_form_generates_files(tmp_path):
    html = _run_demo({"output_dir": str(tmp_path), "review": "on"})

    today = datetime.now().strftime("%Y%m%d")
    assert "Demo 已生成" in html
    assert (tmp_path / f"差旅汇总_demo_{today}.xlsx").exists()
    assert (tmp_path / f"review_{today}.html").exists()


def test_scan_form_validates_inputs():
    assert _validate_scan_inputs("2026-07-01", "2026-07-29", "60") is None
    assert _validate_scan_inputs("2026/07/01", None, "60") == "开始日期必须使用 YYYY-MM-DD 格式。"
    assert _validate_scan_inputs(None, "2026-07-99", "60") == "结束日期必须使用 YYYY-MM-DD 格式。"
    assert _validate_scan_inputs(None, None, "abc") == "扫描邮件数量必须是整数。"
    assert _validate_scan_inputs(None, None, "0") == "扫描邮件数量必须大于 0。"


def test_web_scan_form_passes_safe_args(monkeypatch, tmp_path):
    captured = {}

    def fake_scan(args):
        captured["args"] = args
        tmp_path.joinpath("records_20260729.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr("biztrip_agent.cli.scan", fake_scan)
    monkeypatch.setattr("biztrip_agent.web._preflight_scan", lambda _output_dir: None)

    payload = _run_scan(
        {
            "start": "2026-07-01",
            "end": "2026-07-29",
            "count": "25",
            "output_dir": str(tmp_path),
            "review": "on",
            "no_llm": "on",
        }
    )
    deadline = time.time() + 2
    snapshot = _job_snapshot(payload["job_id"])
    while snapshot["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.02)
        snapshot = _job_snapshot(payload["job_id"])

    args = captured["args"]
    assert snapshot["status"] == "succeeded"
    assert args.start == "2026-07-01"
    assert args.end == "2026-07-29"
    assert args.count == 25
    assert args.output_dir == str(tmp_path)
    assert args.review is True
    assert args.no_llm is True
    assert "EMAIL_PASSWORD" not in str(snapshot)
    assert "LLM_API_KEY" not in str(snapshot)


def test_scan_preflight_requires_email_config(tmp_path):
    assert _preflight_scan(tmp_path) == "请先在 .env 中填写 EMAIL_ACCOUNT。"


def test_background_job_records_failure():
    def fail():
        raise RuntimeError("authentication failed")

    job_id = _start_job("测试任务", fail)
    deadline = time.time() + 2
    snapshot = _job_snapshot(job_id)
    while snapshot["status"] in {"queued", "running"} and time.time() < deadline:
        time.sleep(0.02)
        snapshot = _job_snapshot(job_id)

    assert snapshot["status"] == "failed"
    assert "邮箱登录失败" in snapshot["message"]


def test_result_summary_reads_latest_records_json(tmp_path):
    records_path = tmp_path / "records_20260729.json"
    records_path.write_text(
        '{"scan_label":"7月","summary":{"record_count":3,"trip_count":1,"total_amount":456.7}}',
        encoding="utf-8",
    )

    summary = _result_summary(tmp_path)

    assert summary["scan_label"] == "7月"
    assert summary["record_count"] == 3
    assert summary["trip_count"] == 1
    assert summary["total_amount"] == 456.7


def test_friendly_error_maps_common_failures():
    assert "邮箱登录失败" in _friendly_error(RuntimeError("authentication failed"))
    assert "网络连接失败" in _friendly_error(RuntimeError("timed out"))


def test_readiness_status_does_not_expose_secret_values(tmp_path):
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "EMAIL_ACCOUNT=user@example.com",
                "EMAIL_PASSWORD=super-secret-mail-token",
                "LLM_API_KEY=sk-super-secret",
            ]
        ),
        encoding="utf-8",
    )

    statuses = readiness_status(tmp_path)
    rendered = render_home()

    assert any(item["label"] == "邮箱授权码" and item["detail"] == "已填写" for item in statuses)
    assert "super-secret-mail-token" not in str(statuses)
    assert "sk-super-secret" not in str(statuses)
    assert "super-secret-mail-token" not in rendered
    assert "sk-super-secret" not in rendered


def test_web_home_supports_head_request():
    server = ThreadingHTTPServer(("127.0.0.1", 0), BizTripWebHandler)
    thread = Thread(target=server.serve_forever)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port, timeout=2)
        conn.request("HEAD", "/")
        response = conn.getresponse()
        response.read()
        conn.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert response.status == 200
    assert int(response.getheader("Content-Length")) > 0
