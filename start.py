"""One-command local launcher for non-technical users."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"


def main() -> int:
    if sys.version_info < (3, 8):
        print("需要先安装 Python 3.8 或更高版本。")
        print("macOS 可从 https://www.python.org/downloads/ 下载安装。")
        return 1

    python = _venv_python()
    if not python.exists():
        print("首次启动：正在创建本地运行环境...")
        result = subprocess.run([sys.executable, "-m", "venv", str(VENV)], cwd=ROOT)
        if result.returncode != 0:
            return result.returncode

    print("正在安装或更新 BizTrip Agent 依赖...")
    result = subprocess.run([str(python), "-m", "pip", "install", "-e", "."], cwd=ROOT)
    if result.returncode != 0:
        return result.returncode

    print("正在启动本地 Web 工作台...")
    print("如果浏览器没有自动打开，请访问：http://127.0.0.1:8765/")
    return subprocess.run([str(python), "-m", "biztrip_agent.cli", "web"], cwd=ROOT).returncode


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


if __name__ == "__main__":
    raise SystemExit(main())
