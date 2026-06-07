"""
全局配置。所有跨模块常量集中在这里，避免散落。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


# ---------- 路径 ----------
PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "智能助手"

# 数据目录：%APPDATA%/智能助手，开发态回退到项目根 .data/
def _data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        d = Path(appdata) / APP_NAME
    else:
        d = PROJECT_ROOT / ".data"
    d.mkdir(parents=True, exist_ok=True)
    return d


DATA_DIR = _data_dir()
MEMORY_FILE = DATA_DIR / "memory.json"
LOG_FILE = DATA_DIR / "app.log"


# ---------- LLM 提供方 ----------
# 每个 provider 自带：显示名 / 协议 (openai / anthropic) / base_url / 预置模型列表 / 默认模型
# 用户只需填 API Key，其它（base_url / 模型）由 UI 选择后从这张表里取。

PROVIDERS: dict[str, dict] = {
    "deepseek": {
        "name": "DeepSeek",
        "type": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "key_hint": "sk-…  (DeepSeek 开放平台)",
    },
    "minimax": {
        "name": "minimax",
        "type": "openai",
        "base_url": "https://api.MiniMax.chat/v1",
        "models": ["MiniMax-Text-01", "abab6.5s-chat", "abab6.5g-chat"],
        "default_model": "MiniMax-Text-01",
        "key_hint": "API Key  (minimax 开放平台)",
    },
    "qwen": {
        "name": "Qwen 通义千问",
        "type": "openai",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwq-plus", "qwen-long"],
        "default_model": "qwen-plus",
        "key_hint": "sk-…  (阿里云 DashScope)",
    },
    "openai": {
        "name": "ChatGPT (OpenAI)",
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "models": [
            "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo",
            "o1", "o1-mini", "o1-preview", "o3-mini",
        ],
        "default_model": "gpt-4o-mini",
        "key_hint": "sk-…  (OpenAI Platform)",
    },
    "anthropic": {
        "name": "Claude (Anthropic)",
        "type": "anthropic",
        "base_url": "https://api.anthropic.com",
        "models": [
            "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest",
            "claude-3-opus-latest", "claude-3-5-sonnet-20241022",
        ],
        "default_model": "claude-3-5-sonnet-latest",
        "key_hint": "sk-ant-…  (Anthropic Console)",
    },
}

PROVIDER_ORDER = ["deepseek", "minimax", "qwen", "openai", "anthropic"]


def current_provider_key() -> str:
    try:
        import settings
        k = settings.get("provider", "openai")
        if k in PROVIDERS:
            return k
    except Exception:
        pass
    return "openai"


def current_provider() -> dict:
    return PROVIDERS[current_provider_key()]


def current_model() -> str:
    try:
        import settings
        m = settings.get("model", "")
        if m:
            return str(m)
    except Exception:
        pass
    return current_provider()["default_model"]


def current_api_key() -> str:
    try:
        import settings
        keys = settings.get("api_keys", {}) or {}
        if isinstance(keys, dict):
            return str(keys.get(current_provider_key(), "") or "").strip()
    except Exception:
        pass
    return ""


def current_base_url() -> str:
    """优先用 settings.base_urls[provider] 的自定义值,否则用 provider 默认。"""
    try:
        import settings
        urls = settings.get("base_urls", {}) or {}
        if isinstance(urls, dict):
            u = urls.get(current_provider_key())
            if u:
                return str(u)
    except Exception:
        pass
    return current_provider()["base_url"]


# 兼容旧字段读取（仅供 .env 兜底；正常流程已切换到 PROVIDERS）
def api_key() -> str:
    k = current_api_key()
    if k:
        return k
    return os.getenv("OPENAI_API_KEY", "").strip()


def base_url() -> str:
    return current_base_url()


def model() -> str:
    return current_model()


REQUEST_TIMEOUT = 60
MAX_HISTORY_TURNS = 10  # 进 context 的最近对话轮数


# ---------- 联网搜索 ----------
SEARCH_TIMEOUT = 10
SEARCH_MAX_RESULTS = 5
# 含这些词就触发联网（最简的 tool-call 替代）
SEARCH_TRIGGERS = (
    "搜索", "搜一下", "查一下", "百度", "google", "谷歌",
    "最新", "今天", "昨天", "今年", "新闻", "现在",
)


# ---------- 全局快捷键：连按三下空格 ----------
HOTKEY_WINDOW_MS = 1200   # 三次空格总窗口
HOTKEY_GAP_MS = 450       # 两次空格最大间隔
HOTKEY_PRESSES = 3


# ---------- UI ----------
WINDOW_WIDTH = 460
WINDOW_HEIGHT = 520
WINDOW_MARGIN = 12        # 距离屏幕边缘的最小留白


# ---------- 开机自启 ----------
AUTOSTART_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_APP_NAME = "SmartAssistant"


def is_frozen() -> bool:
    """是否打包成 exe（PyInstaller）"""
    return getattr(sys, "frozen", False)


def entry_path() -> str:
    """打包后用 exe 路径，否则用 pythonw + app.py"""
    if is_frozen():
        return sys.executable
    # 用 pythonw 避免控制台黑窗
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    runner = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{runner}" "{PROJECT_ROOT / "app.py"}"'
