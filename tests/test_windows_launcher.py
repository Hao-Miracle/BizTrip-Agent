import os
from pathlib import Path

from windows_launcher import app_data_dir, available_port, prepare_runtime, reports_dir


def test_windows_paths_use_local_app_data_and_explicit_output(tmp_path):
    environ = {
        "LOCALAPPDATA": str(tmp_path / "local"),
        "BIZTRIP_OUTPUT_DIR": str(tmp_path / "reports"),
    }

    assert app_data_dir(environ) == tmp_path / "local" / "BizTripAgent"
    assert reports_dir(environ) == tmp_path / "reports"


def test_prepare_runtime_persists_config_and_reports_outside_executable(monkeypatch, tmp_path):
    data_dir = tmp_path / "private"
    output_dir = tmp_path / "documents" / "BizTrip Agent"
    environ = {
        "BIZTRIP_DATA_DIR": str(data_dir),
        "BIZTRIP_OUTPUT_DIR": str(output_dir),
    }
    original_cwd = Path.cwd()

    try:
        prepared_data, prepared_output = prepare_runtime(environ)
    finally:
        os.chdir(original_cwd)

    assert prepared_data == data_dir
    assert prepared_output == output_dir
    assert data_dir.exists()
    assert output_dir.exists()
    assert environ["BIZTRIP_ENV_PATH"] == str(data_dir / ".env")


def test_available_port_returns_a_bindable_port():
    port = available_port(0)

    assert 1 <= port <= 65535
