import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills" / "biztrip-reimbursement" / "scripts" / "install_engine.py"
SPEC = importlib.util.spec_from_file_location("biztrip_skill_installer", SCRIPT)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)


def test_check_reports_missing_engine_without_installing(tmp_path, capsys):
    target = tmp_path / "engine"

    exit_code = INSTALLER.main(["--check", "--install-dir", str(target)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "not_installed"
    assert payload["engine_command"] == ""
    assert not target.exists()


def test_check_returns_existing_isolated_engine_command(tmp_path, capsys):
    target = tmp_path / "engine"
    command = (
        target / ".venv" / "Scripts" / "biztrip.exe"
        if INSTALLER.os.name == "nt"
        else target / ".venv" / "bin" / "biztrip"
    )
    command.parent.mkdir(parents=True)
    command.write_text("launcher", encoding="utf-8")

    exit_code = INSTALLER.main(["--check", "--install-dir", str(target)])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "ready"
    assert payload["engine_command"] == str(command)
    assert payload["web_command"] == f"{command} web"


def test_safe_extract_rejects_parent_directory_escape(tmp_path):
    from zipfile import ZipFile

    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as bundle:
        bundle.writestr("../outside.txt", "unsafe")

    with ZipFile(archive) as bundle:
        try:
            INSTALLER._safe_extract(bundle, tmp_path / "extract")
        except ValueError as exc:
            assert "unsafe" in str(exc)
        else:
            raise AssertionError("unsafe archive path must be rejected")


def test_limited_download_rejects_oversized_content(tmp_path):
    from io import BytesIO

    destination = BytesIO()
    try:
        INSTALLER._copy_limited(BytesIO(b"12345"), destination, 4)
    except ValueError as exc:
        assert "too large" in str(exc)
    else:
        raise AssertionError("oversized download must be rejected")
