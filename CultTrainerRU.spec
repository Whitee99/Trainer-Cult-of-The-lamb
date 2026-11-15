# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['trainer.py'],
    pathex=[],
    binaries=[],
    datas=[('plugin/CultTrainer.dll', 'plugin'), ('tools/bepinex', 'tools/bepinex'), ('assets/icon.ico', 'assets'), ('THIRD_PARTY_NOTICES.md', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy'],
    noarchive=False,
    optimize=0,
)
# Qt 6.12 uses the Windows ICU API. A different icuuc.dll from the host's
# Poppler toolchain can be discovered on PATH; it must not shadow Windows ICU.
a.binaries = [entry for entry in a.binaries if entry[0].replace('\\', '/').split('/')[-1].lower() != 'icuuc.dll']
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CultTrainerRU',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)
