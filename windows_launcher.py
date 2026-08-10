"""One-click Windows launcher for the packaged BizTrip Agent executable."""

import os
import shutil
import socket
import sys
import traceback
from pathlib import Path


APP_NAME = "BizTripAgent"
DEFAULT_PORT = 8765


def app_data_dir(environ=None):
    """Return the persistent private directory for config and logs."""
    environ = os.environ if environ is None else environ
    override = environ.get("BIZTRIP_DATA_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    local_app_data = environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def reports_dir(environ=None):
    """Return the user-visible directory for generated reimbursement files."""
    environ = os.environ if environ is None else environ
    override = environ.get("BIZTRIP_OUTPUT_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    documents = Path.home() / "Documents"
    if documents.exists():
        return documents / "BizTrip Agent"
    return app_data_dir(environ) / "output"


def resource_path(name):
    """Resolve a bundled PyInstaller resource or a source checkout file."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / name


def prepare_runtime(environ=None):
    """Create persistent directories and configure the application runtime."""
    environ = os.environ if environ is None else environ
    data_dir = app_data_dir(environ)
    output_dir = reports_dir(environ)
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    env_path = data_dir / ".env"
    example_target = data_dir / ".env.example"
    example_source = resource_path(".env.example")
    if not example_target.exists() and example_source.exists():
        shutil.copyfile(example_source, example_target)

    environ["BIZTRIP_DATA_DIR"] = str(data_dir)
    environ["BIZTRIP_OUTPUT_DIR"] = str(output_dir)
    environ["BIZTRIP_ENV_PATH"] = str(env_path)
    os.chdir(data_dir)
    return data_dir, output_dir


def available_port(preferred=DEFAULT_PORT):
    """Use the familiar port when available, otherwise choose a free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", preferred))
        except OSError:
            probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def configured_port(environ=None):
    """Use an explicit deployment port, or automatically find one."""
    environ = os.environ if environ is None else environ
    value = environ.get("BIZTRIP_PORT", "").strip()
    if not value:
        return available_port()
    port = int(value)
    if not 1 <= port <= 65535:
        raise ValueError("BIZTRIP_PORT must be between 1 and 65535")
    return port


def show_error(message):
    """Display launch failures even though the packaged app has no console."""
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "BizTrip Agent 启动失败", 0x10)
    except Exception:
        print(message)


def main():
    data_dir, _output_dir = prepare_runtime()
    log_path = data_dir / "biztrip-agent.log"
    try:
        with log_path.open("a", encoding="utf-8") as log:
            sys.stdout = log
            sys.stderr = log
            port = configured_port()
            from biztrip_agent.web import run_server

            open_browser = os.getenv("BIZTRIP_NO_OPEN_BROWSER") != "1"
            return run_server(host="127.0.0.1", port=port, open_browser=open_browser)
    except Exception:
        details = traceback.format_exc()
        try:
            log_path.write_text(details, encoding="utf-8")
        except OSError:
            pass
        show_error(f"程序无法启动。请把这个日志文件发给维护者：\n{log_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
