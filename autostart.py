"""
Windows 开机自启：通过写 HKCU\\...\\Run 注册表实现（用户级，不需要管理员权限）。

只支持 Windows；其他平台返回 False。
"""
from __future__ import annotations

import sys
import platform

import config


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_enabled() -> bool:
    if not _is_windows():
        return False
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            config.AUTOSTART_REG_KEY,
            0, winreg.KEY_READ,
        ) as key:
            try:
                value, _ = winreg.QueryValueEx(key, config.AUTOSTART_APP_NAME)
                return bool(value)
            except FileNotFoundError:
                return False
    except OSError:
        return False


def enable() -> tuple[bool, str]:
    if not _is_windows():
        return False, "仅支持 Windows"
    try:
        import winreg
        cmd = config.entry_path()
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            config.AUTOSTART_REG_KEY,
            0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(
                key, config.AUTOSTART_APP_NAME, 0,
                winreg.REG_SZ, cmd,
            )
        return True, f"已开启自启：{cmd}"
    except OSError as e:
        return False, f"写入注册表失败：{e}"


def disable() -> tuple[bool, str]:
    if not _is_windows():
        return False, "仅支持 Windows"
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            config.AUTOSTART_REG_KEY,
            0, winreg.KEY_SET_VALUE,
        ) as key:
            try:
                winreg.DeleteValue(key, config.AUTOSTART_APP_NAME)
                return True, "已关闭自启"
            except FileNotFoundError:
                return True, "自启本来就是关闭的"
    except OSError as e:
        return False, f"删除注册表失败：{e}"


if __name__ == "__main__":
    # 命令行：python autostart.py on / off / status
    if len(sys.argv) < 2:
        print("usage: python autostart.py on|off|status")
        sys.exit(1)
    op = sys.argv[1].lower()
    if op == "on":
        ok, msg = enable()
    elif op == "off":
        ok, msg = disable()
    elif op == "status":
        print("enabled" if is_enabled() else "disabled")
        sys.exit(0)
    else:
        print("unknown op")
        sys.exit(1)
    print(msg)
    sys.exit(0 if ok else 1)
