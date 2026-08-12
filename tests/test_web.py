from http.client import HTTPConnection
from threading import Thread
import json
import os
import time

from http.server import ThreadingHTTPServer

from biztrip_agent.cli import main
from biztrip_agent.web import (
    BizTripWebHandler,
    _agent_resolution_html,
    _friendly_error,
    _infer_imap_server,
    _env_path,
    _job_snapshot,
    _onboarding_html,
    _provider_setup_hint,
    _parse_post_form,
    _preflight_scan,
    _read_env_values,
    _result_summary,
    _run_account,
    _run_config,
    _shutdown_html,
    _run_demo,
    _run_scan,
    _summary_html,
    _start_job,
    _using_temporary_env,
    _valid_attachment_content,
    _validate_scan_inputs,
    _write_env_values,
    readiness_status,
    render_home,
)


def test_web_home_contains_local_workflows(monkeypatch, tmp_path):
    monkeypatch.setenv("BIZTRIP_ENV_PATH", str(tmp_path / "test.env"))
    html = render_home()

    assert "BizTrip Agent" in html
    assert "配置与报销文件保存在本机" in html
    assert 'action="/demo"' in html
    assert 'action="/rebuild"' not in html
    assert 'action="/scan"' in html
    assert 'action="/init"' in html
    assert 'action="/config"' in html
    assert "账号" in html
    assert "生成报销包" in html
    assert "保存账号" in html
    assert "报销开始日期" in html
    assert "报销结束日期" in html
    assert "高级扫描选项" in html
    assert "维护工具" in html
    assert "个人版 Agent 模型" in html
    assert "通过 Skill 做体检时复用你 Agent 的模型" in html
    assert "接口地址" in html
    assert "API Key" in html
    assert "模型名称" in html
    assert "低成本模型" in html
    assert "云端模型会接收必要的邮件和票据文本" in html
    assert "提供商" not in html
    assert "准备状态" in html
    assert "诊断信息" in html
    assert "打开报销文件夹" in html
    assert "安全停止程序" in html


def test_windows_output_directory_is_used_in_forms(monkeypatch, tmp_path):
    output_dir = tmp_path / "Documents" / "BizTrip Agent"
    monkeypatch.setenv("BIZTRIP_OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("BIZTRIP_ENV_PATH", str(tmp_path / ".env"))

    html = render_home()

    assert str(output_dir) in html


def test_shutdown_page_explains_how_to_restart():
    html = _shutdown_html()

    assert "已安全停止" in html
    assert "重新打开 BizTrip Agent" in html


def test_web_env_path_can_use_temporary_first_run_config(monkeypatch, tmp_path):
    env_path = tmp_path / "first-run.env"
    monkeypatch.setenv("BIZTRIP_ENV_PATH", str(env_path))

    assert _env_path() == env_path
    html = render_home()
    assert _using_temporary_env() is True
    assert "第一次使用" in html
    assert "最近结果" not in html
    assert "生成文件" not in html


def test_web_never_shows_saved_results_on_fresh_home(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "records_20260731_120000.json").write_text(
        '{"scan_label":"旧结果","summary":{"record_count":9,"trip_count":3,"total_amount":1234.5}}',
        encoding="utf-8",
    )
    package_dir = output_dir / "报销包_20260731_120000"
    package_dir.mkdir()
    (package_dir / "差旅汇总_20260731_120000.xlsx").write_text("demo", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BIZTRIP_ENV_PATH", raising=False)
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    html = render_home()

    assert "第一次使用" in html
    assert "旧结果" not in html
    assert "最近结果" not in html
    assert "生成文件" not in html

    env_path.write_text("EMAIL_ACCOUNT=user@qq.com\nEMAIL_PASSWORD=token\n", encoding="utf-8")
    html = render_home()

    assert "旧结果" not in html
    assert "最近结果" not in html
    assert "生成文件" not in html


def test_first_run_onboarding_guides_account_setup():
    html = _onboarding_html({}, configured=False)

    assert "第一次使用" in html
    assert "开启 IMAP/SMTP 服务" in html
    assert "生成邮箱授权码" in html
    assert "不要使用登录密码" in html
    assert "不同邮箱怎么拿授权码" in html
    assert "QQ 邮箱" in html
    assert "163/126 邮箱" in html
    assert "Gmail" in html
    assert "Outlook/Hotmail" in html


def test_first_run_onboarding_hides_after_configured():
    assert _onboarding_html({"EMAIL_ACCOUNT": "user@qq.com"}, configured=True) == ""


def test_provider_setup_hint_matches_common_email_domains():
    assert "QQ 邮箱" in _provider_setup_hint("user@qq.com")
    assert "网易邮箱" in _provider_setup_hint("user@163.com")
    assert "Gmail" in _provider_setup_hint("user@gmail.com")
    assert "常见邮箱" in _provider_setup_hint("user@example.com")


def test_web_rejects_invalid_port():
    assert main(["web", "--port", "70000"]) == 2


def test_web_demo_form_generates_files(tmp_path):
    html = _run_demo({"output_dir": str(tmp_path), "review": "on"})

    assert "Demo 已生成" in html
    assert next(tmp_path.glob("差旅汇总_demo_*.xlsx")).exists()
    assert next(tmp_path.glob("review_*.html")).exists()


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


def test_web_primary_scan_uses_user_reimbursement_period(monkeypatch, tmp_path):
    captured = {}

    def fake_scan(args):
        captured["args"] = args
        tmp_path.joinpath("records_20260730_120000.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr("biztrip_agent.cli.scan", fake_scan)
    monkeypatch.setattr("biztrip_agent.web._preflight_scan", lambda _output_dir: None)

    payload = _run_scan(
        {
            "start": "2026-07-01",
            "end": "2026-07-30",
            "count": "60",
            "output_dir": str(tmp_path),
            "review": "on",
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
    assert args.end == "2026-07-30"
    assert args.count == 60


def test_account_form_saves_config_and_infers_imap(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    html = _run_account(
        {
            "EMAIL_ACCOUNT": "user@qq.com",
            "EMAIL_PASSWORD": "mail-token",
        }
    )

    values = _read_env_values(env_path)
    assert "邮箱已保存" in html
    assert values["EMAIL_ACCOUNT"] == "user@qq.com"
    assert values["EMAIL_PASSWORD"] == "mail-token"
    assert values["EMAIL_IMAP_SERVER"] == "imap.qq.com"
    assert values["EMAIL_IMAP_PORT"] == "993"


def test_account_form_requires_password_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: tmp_path / ".env")

    html = _run_account({"EMAIL_ACCOUNT": "user@qq.com", "EMAIL_PASSWORD": ""})

    assert "请填写邮箱授权码" in html


def test_infer_imap_server_from_email_address():
    assert _infer_imap_server("user@qq.com") == "imap.qq.com"
    assert _infer_imap_server("user@163.com") == "imap.163.com"
    assert _infer_imap_server("user@gmail.com") == "imap.gmail.com"
    assert _infer_imap_server("user@example.com") == ""


def test_scan_preflight_requires_email_config(monkeypatch, tmp_path):
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: tmp_path / ".env")

    assert _preflight_scan(tmp_path) == "请先在 .env 中填写 EMAIL_ACCOUNT。"


def test_scan_preflight_requires_agent_model_config(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("EMAIL_ACCOUNT=user@qq.com\nEMAIL_PASSWORD=mail-token\n", encoding="utf-8")
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    assert _preflight_scan(tmp_path) == "请先配置 Agent 模型 API Key。"

    env_path.write_text(
        "EMAIL_ACCOUNT=user@qq.com\nEMAIL_PASSWORD=mail-token\nLLM_API_KEY=sk-test\n",
        encoding="utf-8",
    )
    assert _preflight_scan(tmp_path) == "请先配置 Agent 模型接口地址。"


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
    assert summary["submission_status"] == "unknown"


def test_result_summary_reports_actual_llm_usage(tmp_path):
    state_dir = tmp_path / ".biztrip"
    state_dir.mkdir()
    (state_dir / "records_20260812_120000.json").write_text(
        json.dumps(
            {
                "scan_label": "测试范围",
                "summary": {"record_count": 2},
                "records": [{"提取方式": "LLM"}, {"提取方式": "规则"}],
                "files": {"review": "output/review_test.html"},
                "agent_task": {"mode": "agent"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = _result_summary(tmp_path)

    assert summary["task_mode"] == "agent"
    assert summary["llm_count"] == 1
    assert summary["rule_count"] == 1
    assert "Agent 模式" in _summary_html(summary)


def test_summary_html_shows_submission_verdict():
    html = _summary_html(
        {
            "scan_label": "7月",
            "record_count": 3,
            "trip_count": 1,
            "total_amount": 456.7,
            "submission_status": "needs_review",
            "affected_count": 2,
            "issue_count": 3,
        }
    )

    assert "暂不建议提交" in html
    assert "2 条记录需要处理" in html
    assert "已识别金额" in html
    assert "待处理记录" in html


def test_agent_resolution_html_shows_only_editable_open_fields(tmp_path):
    (tmp_path / "records_20260810.json").write_text(
        '{"agent_task":{"questions":[{"record_index":1,'
        '"issue_codes":["missing_amount","missing_attachment"],'
        '"prompt":"请确认金额并补充原件",'
        '"context":{"主题":"电子发票"}}]}}',
        encoding="utf-8",
    )

    page = _agent_resolution_html(tmp_path)

    assert "Agent 需要你确认" in page
    assert "电子发票" in page
    assert 'name="answer_1_missing_amount"' in page
    assert 'name="answer_1_missing_attachment"' in page
    assert 'enctype="multipart/form-data"' in page


def test_multipart_parser_keeps_text_and_uploaded_bytes():
    boundary = "biztrip-boundary"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"json_path\"\r\n\r\n/tmp/result.json\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"answer_1_missing_attachment\"; filename=\"invoice.pdf\"\r\n"
        "Content-Type: application/pdf\r\n\r\nPDF-DATA\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    form = _parse_post_form(f"multipart/form-data; boundary={boundary}", body)

    assert form["json_path"] == "/tmp/result.json"
    assert form["answer_1_missing_attachment"]["filename"] == "invoice.pdf"
    assert form["answer_1_missing_attachment"]["data"] == b"PDF-DATA"


def test_uploaded_attachment_content_must_match_extension():
    assert _valid_attachment_content(".pdf", b"%PDF-1.7 content") is True
    assert _valid_attachment_content(".png", b"\x89PNG\r\n\x1a\ncontent") is True
    assert _valid_attachment_content(".pdf", b"renamed executable") is False


def test_friendly_error_maps_common_failures():
    qq_error = (
        "Login fail. Account is abnormal, service is not open, password is incorrect, "
        "login frequency limited, or system is busy. More information at "
        "https://help.mail.qq.com/detail/108/1023"
    )
    assert "QQ 邮箱登录失败" in _friendly_error(RuntimeError(qq_error))
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


def test_env_writer_preserves_comments_and_updates_values(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("# config\nEMAIL_ACCOUNT=old@example.com\nEMAIL_PASSWORD=old-token\n", encoding="utf-8")

    _write_env_values(env_path, {"EMAIL_ACCOUNT": "new@example.com", "EMAIL_IMAP_SERVER": "imap.example.com"})

    text = env_path.read_text(encoding="utf-8")
    assert "# config" in text
    assert "EMAIL_ACCOUNT=new@example.com" in text
    assert "EMAIL_PASSWORD=old-token" in text
    assert "EMAIL_IMAP_SERVER=imap.example.com" in text
    assert _read_env_values(env_path)["EMAIL_ACCOUNT"] == "new@example.com"


def test_env_writer_updates_running_process_and_resets_llm_client(monkeypatch, tmp_path):
    import phase2.llm_extract as llm_extract

    env_path = tmp_path / ".env"
    monkeypatch.setenv("LLM_BASE_URL", "https://old.example.com/v1")
    llm_extract._client = False

    _write_env_values(env_path, {"LLM_BASE_URL": "https://new.example.com/v1"})

    assert os.environ["LLM_BASE_URL"] == "https://new.example.com/v1"
    assert llm_extract._client is None


def test_llm_config_saves_without_overwriting_blank_secret(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("EMAIL_ACCOUNT=old@example.com\nEMAIL_PASSWORD=keep-me\nLLM_API_KEY=keep-key\n", encoding="utf-8")
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    html = _run_config(
        {
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "https://api.example.com/v1",
            "LLM_MODEL": "example-chat",
        }
    )

    values = _read_env_values(env_path)
    assert "配置已保存" in html
    assert values["EMAIL_ACCOUNT"] == "old@example.com"
    assert values["EMAIL_PASSWORD"] == "keep-me"
    assert values["LLM_API_KEY"] == "keep-key"
    assert values["LLM_BASE_URL"] == "https://api.example.com/v1"
    assert values["LLM_MODEL"] == "example-chat"
    assert "keep-me" not in html
    assert "keep-key" not in html


def test_config_form_defaults_llm_provider_when_key_is_added(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("EMAIL_ACCOUNT=user@example.com\nEMAIL_PASSWORD=keep-me\n", encoding="utf-8")
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    html = _run_config(
        {
            "EMAIL_ACCOUNT": "user@example.com",
            "LLM_API_KEY": "sk-test",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
        }
    )

    values = _read_env_values(env_path)
    assert "配置已保存" in html
    assert values["LLM_API_KEY"] == "sk-test"
    assert values["LLM_BASE_URL"] == "https://api.deepseek.com/v1"
    assert values["LLM_MODEL"] == "deepseek-chat"
    assert "sk-test" not in html


def test_llm_config_can_be_saved_separately(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("EMAIL_ACCOUNT=user@example.com\nEMAIL_PASSWORD=keep-me\n", encoding="utf-8")
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    html = _run_config(
        {
            "LLM_BASE_URL": "http://127.0.0.1:8000/v1",
            "LLM_API_KEY": "sk-test",
            "LLM_MODEL": "Qwen3.5-9B",
        }
    )

    values = _read_env_values(env_path)
    assert "配置已保存" in html
    assert values["EMAIL_ACCOUNT"] == "user@example.com"
    assert values["LLM_BASE_URL"] == "http://127.0.0.1:8000/v1"
    assert values["LLM_API_KEY"] == "sk-test"
    assert values["LLM_MODEL"] == "Qwen3.5-9B"


def test_config_form_keeps_existing_custom_llm_provider(monkeypatch, tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "EMAIL_ACCOUNT=user@example.com\n"
        "EMAIL_PASSWORD=keep-me\n"
        "LLM_API_KEY=keep-key\n"
        "LLM_BASE_URL=https://api.example.com/v1\n"
        "LLM_MODEL=example-chat\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("biztrip_agent.web._env_path", lambda: env_path)

    _run_config(
        {
            "EMAIL_ACCOUNT": "user@example.com",
            "LLM_API_KEY": "",
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
        }
    )

    values = _read_env_values(env_path)
    assert values["LLM_BASE_URL"] == "https://api.example.com/v1"
    assert values["LLM_MODEL"] == "example-chat"


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


def test_home_does_not_show_saved_results_from_previous_run(monkeypatch, tmp_path):
    state_dir = tmp_path / ".biztrip"
    state_dir.mkdir(parents=True)
    (state_dir / "records_old.json").write_text(
        '{"scan_label":"旧记录","summary":{"record_count":99}}',
        encoding="utf-8",
    )
    monkeypatch.setattr("biztrip_agent.web._default_output_dir", lambda: tmp_path)

    html = render_home()

    assert "旧记录" not in html
    assert ">99<" not in html
