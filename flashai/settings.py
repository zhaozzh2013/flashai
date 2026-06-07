"""
用户设置：JSON 持久化。

和 memory.py 的区别：
- memory.py 是动态的对话数据（可被清空、滚动窗口）
- settings.py 是用户偏好配置（用户主动修改，修改即生效）

设置优先级：settings.json 中的非空值 > 环境变量 / .env > 内置默认
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

import config


_lock = threading.RLock()

_DEFAULTS: dict[str, Any] = {
    "version": 2,                     # v2: 引入 provider / api_keys 结构
    "position_mode": "follow_mouse",  # "follow_mouse" | "bottom_center"
    "ui_scale": 1.2,                  # 默认放大：紧凑 0.9 / 默认 1.0 / 舒适 1.1 / 放大 1.2
    "provider": "openai",             # 当前模型提供方 key
    "model": "",                      # 当前模型名（留空则用 provider 的 default）
    "api_keys": {},                   # {provider_key: api_key}
    "autostart": False,               # 由 autostart 单独管理
}


def _migrate_v1_to_v2(data: dict[str, Any]) -> None:
    """把老格式 (api_key / base_url / model) 迁到新格式 (provider / api_keys / model)"""
    if data.get("version", 1) >= 2:
        return
    # 老 api_key → openai 的 key
    old_key = (data.get("api_key") or "").strip()
    if old_key and isinstance(data.get("api_keys"), dict) is False:
        data["api_keys"] = {}
    if old_key:
        data.setdefault("api_keys", {})["openai"] = old_key
    # 老 model 如果在 openai 模型列表里就保留
    old_model = (data.get("model") or "").strip()
    if old_model:
        data["model"] = old_model
    # 老 base_url 只在不是默认 openai 时才有意义，这里简单丢给 openai 的默认（用户可在 UI 切提供方）
    data["version"] = 2

_cache: dict[str, Any] | None = None
_cache_mtime: float = 0.0


def _path() -> Path:
    return config.DATA_DIR / "settings.json"


def load() -> dict[str, Any]:
    """读取设置，带 mtime 缓存。修改文件后下次读取会自动刷新。"""
    global _cache, _cache_mtime
    p = _path()
    if p.exists():
        mtime = p.stat().st_mtime
        if _cache is not None and mtime == _cache_mtime:
            return _cache
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            data = dict(_DEFAULTS)
        # 老版本迁移
        _migrate_v1_to_v2(data)
        for k, v in _DEFAULTS.items():
            data.setdefault(k, v)
        _cache = data
        _cache_mtime = mtime
        return _cache
    _cache = dict(_DEFAULTS)
    _cache_mtime = 0.0
    return _cache


def save(data: dict[str, Any]) -> None:
    global _cache, _cache_mtime
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    with _lock:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(p)
    _cache = data
    _cache_mtime = p.stat().st_mtime


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def set_value(key: str, value: Any) -> None:
    with _lock:
        data = load()
        data[key] = value
        save(data)


def invalidate_cache() -> None:
    """外部直接写文件后调用，强制下次重新读"""
    global _cache, _cache_mtime
    _cache = None
    _cache_mtime = 0.0
