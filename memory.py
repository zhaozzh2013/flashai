"""
记忆模块：把对话历史和用户偏好持久化到 JSON。

- 对话历史：滚动窗口，最多保留 N 条（避免 JSON 无限增长）
- 用户偏好：可由用户主动写入（比如"以后回答简短点"）
- 学习：把用户对回答的"赞/踩"作为偏好记录的一部分
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

import config


_lock = threading.Lock()


_DEFAULT_DATA: dict[str, Any] = {
    "version": 1,
    "history": [],          # [{role, content, ts, feedback?}, ...]
    "preferences": [],      # ["回答简洁", "用中文", ...]
    "stats": {
        "total_queries": 0,
        "created_at": 0,
    },
}


def _ensure_file() -> None:
    p: Path = config.MEMORY_FILE
    if not p.exists():
        with open(p, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_DATA, f, ensure_ascii=False, indent=2)


def _load() -> dict[str, Any]:
    _ensure_file()
    try:
        with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        data = json.loads(json.dumps(_DEFAULT_DATA))
    # 补缺字段
    for k, v in _DEFAULT_DATA.items():
        data.setdefault(k, v if not isinstance(v, dict) else dict(v))
    return data


def _save(data: dict[str, Any]) -> None:
    tmp = config.MEMORY_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(config.MEMORY_FILE)


# ---------- 对话历史 ----------
def add_message(role: str, content: str, feedback: int | None = None) -> None:
    """role: 'user' / 'assistant' / 'system'"""
    with _lock:
        data = _load()
        data["history"].append({
            "role": role,
            "content": content,
            "ts": int(time.time()),
            "feedback": feedback,
        })
        # 滚动窗口：保留最近 200 条
        if len(data["history"]) > 200:
            data["history"] = data["history"][-200:]
        if role == "user":
            data["stats"]["total_queries"] += 1
            if data["stats"].get("created_at", 0) == 0:
                data["stats"]["created_at"] = int(time.time())
        _save(data)


def get_recent_messages(limit: int | None = None) -> list[dict[str, str]]:
    """返回给 LLM 用，只取 role/content，限制轮数"""
    n = limit or config.MAX_HISTORY_TURNS
    with _lock:
        data = _load()
    msgs = data["history"][-n * 2:]  # 每轮 2 条
    return [{"role": m["role"], "content": m["content"]} for m in msgs]


def set_feedback(index_from_end: int, value: int) -> None:
    """对倒数第 N 条 assistant 消息打分（1=赞，-1=踩）"""
    with _lock:
        data = _load()
        history = data["history"]
        # 找到倒数第 N 条 role==assistant
        seen = 0
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("role") == "assistant":
                seen += 1
                if seen == index_from_end:
                    history[i]["feedback"] = value
                    break
        _save(data)


# ---------- 偏好 ----------
def add_preference(text: str) -> None:
    text = text.strip()
    if not text:
        return
    with _lock:
        data = _load()
        if text not in data["preferences"]:
            data["preferences"].append(text)
        _save(data)


def get_preferences() -> list[str]:
    with _lock:
        return list(_load()["preferences"])


def clear_preferences() -> None:
    with _lock:
        data = _load()
        data["preferences"] = []
        _save(data)


# ---------- 统计 ----------
def get_stats() -> dict[str, Any]:
    with _lock:
        return dict(_load()["stats"])


def reset_all() -> None:
    with _lock:
        _save(json.loads(json.dumps(_DEFAULT_DATA)))
