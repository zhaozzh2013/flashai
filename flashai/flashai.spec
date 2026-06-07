# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for 智能助手 / FlashAI.

Build:    pyinstaller flashai.spec
Output:   dist/<APP_NAME>/<APP_NAME>[.exe]  (onedir 模式)

跨平台:Windows 叫 "智能助手",macOS / Linux 叫 "FlashAI"。
"""
import sys
from pathlib import Path

block_cipher = None
THIS_DIR = Path(SPECPATH)  # noqa: F821  (SPECPATH 由 PyInstaller 注入)


def _platform_name() -> str:
    if sys.platform.startswith("win"):
        return "智能助手"
    if sys.platform == "darwin":
        return "FlashAI"
    return "flashai"


def _platform_icon() -> str | None:
    for cand in ("icon.ico", "icon.icns", "icon.png", "assets/icon.ico"):
        p = THIS_DIR / cand
        if p.exists():
            return str(p)
    return None


APP_NAME = _platform_name()
ICON_PATH = _platform_icon()

# pynput 平台相关后端模块(避免在不需要的平台上导入)
PYNPUT_HIDDEN = []
if sys.platform.startswith("win"):
    PYNPUT_HIDDEN += ["pynput.keyboard._win32", "pynput.mouse._win32"]
elif sys.platform == "darwin":
    PYNPUT_HIDDEN += ["pynput.keyboard._darwin", "pynput.mouse._darwin"]
else:
    PYNPUT_HIDDEN += ["pynput.keyboard._xorg", "pynput.mouse._xorg"]


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtSvg",
        *PYNPUT_HIDDEN,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5.QtNetwork",
        "PyQt5.QtWebEngineCore",
        "PyQt5.QtWebEngineWidgets",
        "PyQt5.QtMultimedia",
        "PyQt5.QtMultimediaWidgets",
        "PyQt5.QtSql",
        "PyQt5.QtTest",
        "PyQt5.QtBluetooth",
        "PyQt5.QtNfc",
        "PyQt5.QtPositioning",
        "PyQt5.QtSensors",
        "PyQt5.QtSerialPort",
        "PyQt5.QtXml",
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_kwargs = dict(
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
if ICON_PATH:
    exe_kwargs["icon"] = ICON_PATH

if sys.platform.startswith("win"):
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **exe_kwargs,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        **exe_kwargs,
    )

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)
