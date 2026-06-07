"""
Agent 层：把用户消息送到 LLM，按需触发联网搜索。

流式返回：chat() 用 on_chunk 回调把每个 delta 推给 UI，最后返回完整文本。
支持两种协议：
  - openai  : /chat/completions + SSE  (DeepSeek / minimax / Qwen / OpenAI 兼容)
  - anthropic: /v1/messages + SSE       (Claude)
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Iterator

import requests

import config
import memory
import web_search


SYSTEM_PROMPT_TEMPLATE = """你是用户的桌面智能助手，具备以下特点：
1. 简洁直接，默认用中文回复，除非用户用其他语言提问。
2. 如果系统消息里给了"联网搜索结果"，请基于这些信息回答，并明确标注信息时效。
3. 回答尽量控制在 200 字以内，除非用户明确要求详细。

{preferences_block}
"""


def _build_system_prompt() -> str:
    prefs = memory.get_preferences()
    if prefs:
        block = "用户历史偏好（请尽量遵守）：\n" + "\n".join(f"- {p}" for p in prefs)
    else:
        block = "（暂无用户偏好）"
    return SYSTEM_PROMPT_TEMPLATE.format(preferences_block=block)


def needs_search(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in config.SEARCH_TRIGGERS)


def _proxies() -> dict[str, str] | None:
    p = (os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "").strip()
    if not p:
        return None
    return {"http": p, "https": p}


# ---------- 流式核心：OpenAI 协议 ----------
def _stream_openai(messages: list[dict[str, str]]) -> Iterator[str]:
    key = config.current_api_key()
    if not key:
        yield "（未配置 API Key，请到 设置 → API Key 填写）"
        return

    url = config.current_base_url().rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": config.current_model(),
        "messages": messages,
        "temperature": 0.7,
        "stream": True,
    }
    try:
        resp = requests.post(
            url, headers=headers, json=payload,
            timeout=config.REQUEST_TIMEOUT, proxies=_proxies(), stream=True,
        )
    except requests.RequestException as e:
        yield f"（网络错误：{e}）"
        return

    if resp.status_code != 200:
        snippet = resp.text[:300]
        yield f"（API 错误 {resp.status_code}：{snippet}）"
        return

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            if data == "[DONE]":
                break
            continue
        try:
            chunk = json.loads(data)
        except ValueError:
            continue
        try:
            delta = chunk["choices"][0].get("delta") or {}
            content = delta.get("content")
            if content:
                yield content
        except (KeyError, IndexError):
            continue


# ---------- 流式核心：Anthropic 协议 ----------
def _to_anthropic(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    chat: list[dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_parts.append(m["content"])
        else:
            chat.append({"role": m["role"], "content": m["content"]})
    return ("\n\n".join(system_parts) if system_parts else
            "你是用户的桌面智能助手，简洁直接。"), chat


def _stream_anthropic(messages: list[dict[str, str]]) -> Iterator[str]:
    key = config.current_api_key()
    if not key:
        yield "（未配置 Claude API Key，请到 设置 → API Key 填写）"
        return

    system, chat_msgs = _to_anthropic(messages)
    url = config.current_base_url().rstrip("/") + "/v1/messages"
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": config.current_model(),
        "max_tokens": 4096,
        "system": system,
        "messages": chat_msgs,
        "stream": True,
    }
    try:
        resp = requests.post(
            url, headers=headers, json=payload,
            timeout=config.REQUEST_TIMEOUT, proxies=_proxies(), stream=True,
        )
    except requests.RequestException as e:
        yield f"（网络错误：{e}）"
        return

    if resp.status_code != 200:
        snippet = resp.text[:300]
        yield f"（API 错误 {resp.status_code}：{snippet}）"
        return

    # Anthropic SSE: event: content_block_delta  data: {"delta":{"type":"text_delta","text":"…"}}
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data:"):
            data = line[5:].strip()
            if not data:
                continue
            try:
                ev = json.loads(data)
            except ValueError:
                continue
            t = ev.get("type", "")
            if t == "content_block_delta":
                delta = ev.get("delta") or {}
                text = delta.get("text")
                if text:
                    yield text
            elif t == "message_stop":
                break


def _post_chat_stream(messages: list[dict[str, str]]) -> Iterator[str]:
    ptype = config.current_provider().get("type", "openai")
    if ptype == "anthropic":
        yield from _stream_anthropic(messages)
    else:
        yield from _stream_openai(messages)


# ---------- 公开入口 ----------
def chat(
    user_text: str,
    on_status: Callable[[str], None] | None = None,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    """
    主入口：收用户文本，返回助手完整回复。
    - on_status: 中间状态（从后台线程调用，UI 注意线程安全）
    - on_chunk : 每个 delta 调用一次（用于流式渲染）
    """
    memory.add_message("user", user_text)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": _build_system_prompt()}
    ]
    messages.extend(memory.get_recent_messages())

    # 联网判断
    if needs_search(user_text):
        if on_status:
            try:
                on_status("正在联网搜索…")
            except Exception:
                pass
        results = web_search.search(user_text)
        block = web_search.format_for_prompt(user_text, results)
        if block:
            messages.append({"role": "system", "content": block})

    full_reply = ""
    try:
        for chunk in _post_chat_stream(messages):
            full_reply += chunk
            if on_chunk:
                try:
                    on_chunk(chunk)
                except Exception:
                    pass
    except Exception as e:
        err = f"\n[错误: {e}]"
        full_reply += err
        if on_chunk:
            try:
                on_chunk(err)
            except Exception:
                pass

    memory.add_message("assistant", full_reply)
    return full_reply
