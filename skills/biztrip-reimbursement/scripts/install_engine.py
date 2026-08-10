#!/usr/bin/env python3
"""Install or locate the local BizTrip Agent engine without handling secrets."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path


SOURCE_URL = "https://github.com/Hao-Miracle/BizTrip-Agent/archive/refs/heads/main.zip"
INSTALL_SCHEMA = "biztrip.engine-install.v1"
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 250 * 1024 * 1024


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install-dir", default=str(default_install_dir()))
    args = parser.parse_args(argv)
    target = Path(args.install_dir).expanduser().resolve()

    existing = engine_command(target)
    if existing:
        emit(True, "ready", target, existing)
        return 0
    if args.check:
        emit(False, "not_installed", target, message="本地引擎尚未安装。")
        return 1
    if sys.version_info < (3, 8):
        emit(
            False,
            "python_required",
            target,
            message="安装本地引擎需要 Python 3.8 或更高版本。",
        )
        return 1
    if target.exists():
        emit(
            False,
            "incomplete_installation",
            target,
            message="安装目录已存在但引擎不可用，请检查或移走该目录后重试。",
        )
        return 1

    try:
        install_engine(target)
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        emit(
            False,
            "install_failed",
            target,
            message="本地引擎安装失败，请检查网络和 Python 后重试。",
        )
        return 1

    command = engine_command(target)
    if not command:
        emit(False, "install_failed", target, message="安装完成但未找到启动程序。")
        return 1
    emit(True, "installed", target, command)
    return 0


def default_install_dir():
    configured = os.getenv("BIZTRIP_ENGINE_HOME")
    if configured:
        return Path(configured)
    if os.name == "nt":
        base = Path(os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "BizTripAgent" / "engine"
    return Path.home() / ".local" / "share" / "biztrip-agent" / "engine"


def install_engine(target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="biztrip-download-") as temp_dir:
        archive = Path(temp_dir) / "source.zip"
        request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "BizTrip-Agent-Skill"})
        with urllib.request.urlopen(request, timeout=60) as response, archive.open("wb") as output:
            _copy_limited(response, output, MAX_DOWNLOAD_BYTES)
        extracted = Path(temp_dir) / "source"
        extracted.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            _safe_extract(bundle, extracted)
        roots = [path for path in extracted.iterdir() if path.is_dir()]
        if len(roots) != 1 or not (roots[0] / "setup.py").exists():
            raise ValueError("invalid source archive")
        shutil.copytree(roots[0], target)

    subprocess.run(
        [sys.executable, "-m", "venv", str(target / ".venv")],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    python = venv_python(target)
    subprocess.run(
        [str(python), "-m", "pip", "install", "-e", f"{target}[llm]"],
        cwd=target,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _safe_extract(bundle, destination):
    destination = destination.resolve()
    total_size = 0
    for member in bundle.infolist():
        total_size += member.file_size
        if total_size > MAX_EXTRACTED_BYTES:
            raise ValueError("archive is too large")
        resolved = (destination / member.filename).resolve()
        if destination != resolved and destination not in resolved.parents:
            raise ValueError("unsafe archive path")
    bundle.extractall(destination)


def _copy_limited(source, destination, limit):
    total = 0
    while True:
        chunk = source.read(1024 * 1024)
        if not chunk:
            return
        total += len(chunk)
        if total > limit:
            raise ValueError("download is too large")
        destination.write(chunk)


def venv_python(target):
    if os.name == "nt":
        return target / ".venv" / "Scripts" / "python.exe"
    return target / ".venv" / "bin" / "python"


def engine_command(target):
    if os.name == "nt":
        command = target / ".venv" / "Scripts" / "biztrip.exe"
    else:
        command = target / ".venv" / "bin" / "biztrip"
    return command if command.is_file() else None


def emit(ok, status, target, command=None, message=""):
    payload = {
        "schema_version": INSTALL_SCHEMA,
        "ok": ok,
        "status": status,
        "install_dir": str(target),
        "engine_command": str(command or ""),
        "web_command": f"{command} web" if command else "",
    }
    if message:
        payload["message"] = message
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
