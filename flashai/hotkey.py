"""
全局快捷键监听：连按三下空格触发。

约束：
- 监听器跑在 pynput 自己的线程
- 触发后通过回调通知主线程（不要在 pynput 线程里直接操作 Qt UI）
- 排除输入法/组合键的干扰：只在没有 Ctrl/Alt/Shift 等修饰键时计数
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from pynput import keyboard

import config


class TripleSpaceListener:
    """
    在 N 毫秒窗口内连按 K 次空格 -> 触发 callback
    """

    def __init__(
        self,
        callback: Callable[[], None],
        presses: int = config.HOTKEY_PRESSES,
        window_ms: int = config.HOTKEY_WINDOW_MS,
        gap_ms: int = config.HOTKEY_GAP_MS,
    ):
        self._cb = callback
        self._presses = presses
        self._window_s = window_ms / 1000.0
        self._gap_s = gap_ms / 1000.0

        self._timestamps: list[float] = []
        self._lock = threading.Lock()

        self._listener: keyboard.Listener | None = None
        self._modifier_pressed = False

    # ---------- pynput callbacks ----------
    def _on_press(self, key):
        # 任何修饰键按下都重置计数（避免 Ctrl+Space+Space+Space 误触）
        if key in (
            keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
            keyboard.Key.alt_l, keyboard.Key.alt_r,
            keyboard.Key.shift, keyboard.Key.shift_r,
            keyboard.Key.cmd,
        ):
            with self._lock:
                self._modifier_pressed = True
                self._timestamps.clear()
            return

        if key != keyboard.Key.space:
            return

        with self._lock:
            if self._modifier_pressed:
                return
            now = time.monotonic()
            self._timestamps.append(now)
            # 截断：只保留最近 presses 个
            if len(self._timestamps) > self._presses:
                self._timestamps = self._timestamps[-self._presses:]
            # 清理过期的
            self._timestamps = [
                t for t in self._timestamps if now - t <= self._window_s
            ]
            if len(self._timestamps) >= self._presses:
                # 触发！
                self._timestamps.clear()
                triggered = True
            else:
                triggered = False

        if triggered:
            self._cb()

        # 不吞键：让空格正常进前台 app。
        # 三连击触发时窗口会快速抢焦点，第 4 次空格（如果有）就进输入框。
        return None

    def _on_release(self, key):
        if key in (
            keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
            keyboard.Key.alt_l, keyboard.Key.alt_r,
            keyboard.Key.shift, keyboard.Key.shift_r,
            keyboard.Key.cmd,
        ):
            with self._lock:
                self._modifier_pressed = False
        return None

    # ---------- lifecycle ----------
    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
