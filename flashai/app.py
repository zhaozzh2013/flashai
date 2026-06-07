"""
主入口：创建 QApplication、UI、快捷键监听，连接到一起。

启动流程：
1. 解析命令行（支持 --autostart on/off/status）
2. 创建 QApplication（必须在创建 Qt 对象前）
3. 创建 MainApp（默认隐藏）
4. 启动全局快捷键监听：连按三下空格 -> show_at_cursor
5. exec_()

注意：
- pynput 在 Windows 上不需要管理员权限
- 如果要后台常驻：用 pythonw.exe 启动（见 config.entry_path）
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# 路径保险：避免从奇怪 cwd 启动时找不到模块
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _fix_pyqt5_plugins() -> None:
    """
    PyQt5 5.15.11 + Python 3.14 上 Qt 平台插件自动发现会失败，
    表现为弹窗 'Could not find the Qt platform plugin "windows"'。
    手动把插件目录告诉 Qt 即可绕过。
    必须在 import PyQt5.QtCore 之前调用。
    """
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return
    # 用 importlib.util 只查 spec，不触发 PyQt5 实际加载
    import importlib.util
    spec = importlib.util.find_spec("PyQt5")
    if not spec or not spec.origin:
        return
    plugins_platforms = Path(spec.origin).parent / "Qt5" / "plugins" / "platforms"
    if plugins_platforms.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins_platforms)


_fix_pyqt5_plugins()

from PyQt5 import QtWidgets
from PyQt5.QtCore import QMetaObject, Qt

import autostart
import config
import hotkey
import ui


def _setup_logging() -> None:
    config.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="智能助手")
    p.add_argument("--autostart", choices=["on", "off", "status"], help="管理开机自启")
    return p.parse_args()
   

def _handle_autostart_cmd(op: str) -> int:
    if op == "on":
        ok, msg = autostart.enable()
    elif op == "off":
        ok, msg = autostart.disable()
    else:
        msg = "已开启" if autostart.is_enabled() else "未开启"
        ok = True
    print(msg)   
    return 0 if ok else 1


def main() -> int:
    args = _parse_args()
    if args.autostart:
        return _handle_autostart_cmd(args.autostart)

    _setup_logging()
    log = logging.getLogger("app")
    log.info("启动 %s", config.APP_NAME)
    log.info("数据目录: %s", config.DATA_DIR)

    if not config.current_api_key():
        log.warning("未配置 API Key（%s），agent 会直接返回提示，但不会崩溃",
                    config.current_provider())

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setQuitOnLastWindowClosed(False)  # 隐藏窗口时不退出

    win = ui.MainApp()

    # 快捷键 -> 通过 QueuedConnection 把调用切回主线程
    def _on_hotkey() -> None:
        # 已经在主线程也没问题；QueuedConnection 在同线程下会推迟到事件循环下一轮
        QMetaObject.invokeMethod(win, "show_at_cursor", Qt.QueuedConnection)

    listener = hotkey.TripleSpaceListener(callback=_on_hotkey)
    listener.start()
    log.info("全局快捷键监听已启动：连按三下空格")

    # 进程退出时清理
    def _on_about_to_quit() -> None:
        log.info("退出，停止快捷键监听")
        listener.stop()

    app.aboutToQuit.connect(_on_about_to_quit)

    # 第一次运行时，友好地提示是否开自启
    if not autostart.is_enabled():
        log.info("当前未开启开机自启，可用 `python app.py --autostart on` 开启")

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
