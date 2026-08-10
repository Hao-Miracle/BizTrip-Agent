"""One-click macOS launcher for the packaged BizTrip Agent application."""

import os
import subprocess
import sys
import traceback
from pathlib import Path

from windows_launcher import configured_port, prepare_runtime


APP_NAME = "BizTripAgent"


def mac_data_dir(home=None):
    home = Path(home) if home else Path.home()
    return home / "Library" / "Application Support" / APP_NAME


def mac_reports_dir(home=None):
    home = Path(home) if home else Path.home()
    return home / "Documents" / "BizTrip Agent"


def prepare_mac_runtime(environ=None, home=None):
    environ = os.environ if environ is None else environ
    environ.setdefault("BIZTRIP_DATA_DIR", str(mac_data_dir(home)))
    environ.setdefault("BIZTRIP_OUTPUT_DIR", str(mac_reports_dir(home)))
    return prepare_runtime(environ)


def show_error(message):
    try:
        escaped = message.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(
            ["osascript", "-e", f'display alert "BizTrip Agent 启动失败" message "{escaped}"'],
            check=False,
        )
    except Exception:
        print(message)


def main():
    data_dir, _output_dir = prepare_mac_runtime()
    log_path = data_dir / "biztrip-agent.log"
    try:
        with log_path.open("a", encoding="utf-8") as log:
            sys.stdout = log
            sys.stderr = log
            port = configured_port()
            print(f"Starting BizTrip Agent on 127.0.0.1:{port}", flush=True)
            from biztrip_agent.web import run_server

            open_browser = os.getenv("BIZTRIP_NO_OPEN_BROWSER") != "1"
            return run_server(host="127.0.0.1", port=port, open_browser=open_browser)
    except Exception:
        details = traceback.format_exc()
        try:
            log_path.write_text(details, encoding="utf-8")
        except OSError:
            pass
        show_error(f"程序无法启动。日志文件：\n{log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
