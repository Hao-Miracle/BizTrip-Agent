import os
from pathlib import Path

from mac_launcher import mac_data_dir, mac_reports_dir, prepare_mac_runtime
from windows_launcher import configured_port


def test_mac_paths_use_application_support_and_documents(tmp_path):
    assert mac_data_dir(tmp_path) == tmp_path / "Library" / "Application Support" / "BizTripAgent"
    assert mac_reports_dir(tmp_path) == tmp_path / "Documents" / "BizTrip Agent"


def test_prepare_mac_runtime_persists_data_outside_app_bundle(tmp_path):
    environ = {}
    original_cwd = Path.cwd()

    try:
        data_dir, output_dir = prepare_mac_runtime(environ, home=tmp_path)
    finally:
        os.chdir(original_cwd)

    assert data_dir == tmp_path / "Library" / "Application Support" / "BizTripAgent"
    assert output_dir == tmp_path / "Documents" / "BizTrip Agent"
    assert environ["BIZTRIP_ENV_PATH"] == str(data_dir / ".env")


def test_configured_port_honors_explicit_value():
    assert configured_port({"BIZTRIP_PORT": "8876"}) == 8876
