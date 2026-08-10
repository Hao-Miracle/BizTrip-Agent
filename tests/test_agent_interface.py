import json
from pathlib import Path

import biztrip_agent.agent_interface as agent_interface
from biztrip_agent.agent_interface import (
    AUDIT_SCHEMA,
    INTERFACE_SCHEMA,
    answer_task,
    normalize_answers,
    task_status,
)
from biztrip_agent.agent_task import build_agent_task
from biztrip_agent.cli import main
from biztrip_agent.results import write_results_json


def _task_file(tmp_path, amount=""):
    records = [
        {
            "记录ID": "R0001",
            "分类": "发票",
            "金额": amount,
            "日期": "2026-08-01",
            "供应商": "测试商店",
            "附件": "invoice.pdf",
        }
    ]
    task = build_agent_task(records, [], "整理八月报销", use_llm=True)
    return write_results_json(records, [], tmp_path, "八月", agent_task=task)


def test_status_returns_stable_public_snapshot(tmp_path):
    source = _task_file(tmp_path)

    result = task_status(source)

    assert result["schema_version"] == INTERFACE_SCHEMA
    assert result["ok"] is True
    assert result["status"] == "needs_user_input"
    assert result["next_action"] == "ask_user"
    assert result["questions"][0]["record_index"] == 1
    assert "missing_amount" in result["questions"][0]["issue_codes"]


def test_answer_closes_task_and_returns_new_snapshot(tmp_path):
    (tmp_path / "附件").mkdir()
    (tmp_path / "附件" / "invoice.pdf").write_bytes(b"%PDF-1.7 test")
    source = _task_file(tmp_path)

    result = answer_task(
        source,
        {"answers": [{"record_index": 1, "issue_code": "missing_amount", "value": "88.50"}]},
    )

    assert result["ok"] is True
    assert result["status"] == "completed"
    assert result["next_action"] == "deliver_package"
    assert result["task_path"] != str(source.resolve())
    assert result["files"]["package_dir"]


def test_normalize_answers_rejects_unstructured_input():
    try:
        normalize_answers({"record_1": "88.50"})
    except ValueError as exc:
        assert "answers" in str(exc)
    else:
        raise AssertionError("invalid answers must be rejected")


def test_cli_agent_status_prints_json_only(tmp_path, capsys):
    source = _task_file(tmp_path)

    exit_code = main(["agent", "status", "--task", str(source)])
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["schema_version"] == INTERFACE_SCHEMA
    assert payload["operation"] == "status"


def test_cli_agent_start_hides_human_logs_and_prints_one_json(tmp_path, capsys, monkeypatch):
    source = _task_file(tmp_path)

    def fake_start(**_kwargs):
        print("human progress that must not reach the Skill")
        return {"results_path": str(source)}

    monkeypatch.setattr("phase2.agent_report.main", fake_start)
    monkeypatch.setattr(agent_interface, "_agent_configured", lambda: True)

    exit_code = main(["agent", "start", "--start", "2026-08-01", "--end", "2026-08-31"])
    output = capsys.readouterr().out.strip()
    payload = json.loads(output)

    assert exit_code == 0
    assert payload["operation"] == "start"
    assert "human progress" not in output


def test_agent_start_routes_first_time_user_to_local_setup(capsys, monkeypatch):
    monkeypatch.setattr(agent_interface, "_agent_configured", lambda: False)

    exit_code = main(["agent", "start", "--count", "60"])
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 1
    assert payload["error"]["code"] == "setup_required"
    assert "Agent 模型" in payload["error"]["message"]


def test_cli_agent_audit_uses_email_only_and_never_delivers(tmp_path, capsys, monkeypatch):
    source = _task_file(tmp_path, amount=88.5)
    calls = []

    def fake_audit(**kwargs):
        calls.append(kwargs)
        return {"results_path": str(source)}

    monkeypatch.setattr("phase2.agent_report.main", fake_audit)
    monkeypatch.setattr(agent_interface, "_email_configured", lambda: True)

    exit_code = main(
        ["agent", "audit", "--start", "2026-08-01", "--end", "2026-08-31"]
    )
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["schema_version"] == AUDIT_SCHEMA
    assert payload["status"] == "audit_ready"
    assert payload["files"] == {"package_dir": "", "excel": ""}
    assert payload["next_action"] == "present_audit"
    assert payload["full_package"]["requires"] == "local_personal_app"
    assert calls[0]["no_llm"] is True
    assert calls[0]["deliver"] is False


def test_public_skill_cannot_start_full_package_flow():
    skill = (
        Path(__file__).parents[1]
        / "skills"
        / "biztrip-reimbursement"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "biztrip agent audit" in skill
    assert "biztrip agent start" not in skill
    assert "biztrip agent answer" not in skill
    assert "LLM_API_KEY" not in skill


def test_cli_agent_audit_rejects_more_than_one_month(capsys):
    exit_code = main(
        ["agent", "audit", "--start", "2026-07-01", "--end", "2026-08-01"]
    )
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 1
    assert payload["schema_version"] == AUDIT_SCHEMA
    assert payload["error"]["code"] == "invalid_range"


def test_agent_audit_routes_first_time_user_to_email_setup(capsys, monkeypatch):
    monkeypatch.setattr(agent_interface, "_email_configured", lambda: False)

    exit_code = main(["agent", "audit", "--count", "60"])
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 1
    assert payload["schema_version"] == AUDIT_SCHEMA
    assert payload["error"]["code"] == "setup_required"
    assert "Agent 模型" not in payload["error"]["message"]
    assert "邮箱" in payload["error"]["message"]


def test_cli_agent_answer_reads_structured_file(tmp_path, capsys):
    (tmp_path / "附件").mkdir()
    (tmp_path / "附件" / "invoice.pdf").write_bytes(b"%PDF-1.7 test")
    source = _task_file(tmp_path)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(
        json.dumps(
            {"answers": [{"record_index": 1, "issue_code": "missing_amount", "value": 88.5}]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        ["agent", "answer", "--task", str(source), "--answers-file", str(answers_path)]
    )
    payload = json.loads(capsys.readouterr().out.strip())

    assert exit_code == 0
    assert payload["status"] == "completed"
