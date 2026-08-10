from PyInstaller.utils.hooks import collect_all


openai_datas, openai_binaries, openai_hiddenimports = collect_all("openai")

analysis = Analysis(
    ["mac_launcher.py"],
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
    [],
    exclude_binaries=True,
    name="BizTrip-Agent-Mac",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

collection = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="BizTrip-Agent-Mac",
)

app = BUNDLE(
    collection,
    name="BizTrip-Agent-Mac.app",
    icon=None,
    bundle_identifier="com.haomiracle.biztrip-agent",
    version="0.1.2",
    info_plist={"NSHighResolutionCapable": True},
)
