from PyInstaller.utils.hooks import collect_all


openai_datas, openai_binaries, openai_hiddenimports = collect_all("openai")

analysis = Analysis(
    ["windows_launcher.py"],
    pathex=[],
    binaries=openai_binaries,
    datas=[(".env.example", "."), *openai_datas],
    hiddenimports=openai_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="BizTrip-Agent-Windows",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
