# FlashAI · 智能助手

> **A tiny, fast, Claude-style desktop AI assistant for Windows / macOS / Linux.**
> 三连空格唤起，五家模型随意切，代码 / Markdown / 记忆全都给你。

[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-blue)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org)
[![PyQt5](https://img.shields.io/badge/PyQt5-5.15-green)](https://pypi.org/project/PyQt5/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Release](https://img.shields.io/github/v/release/zhaozzh2013/flashai)](https://github.com/zhaozzh2013/flashai/releases)

---

## ✨ 特性 Features

| 类别 | 说明 |
|---|---|
| 🚀 **三连空格唤起** | 桌面任意位置连按 3 次空格,1.2 s 窗口内生效,Claude / Raycast 同款手感 |
| 🔌 **5 家模型提供方** | DeepSeek · minimax · Qwen · OpenAI · Anthropic,每个独立存 API Key,模型列表只展示当前提供方 |
| ⚡ **流式输出** | SSE 解析 (OpenAI 协议 + Anthropic `content_block_delta` 协议),逐字打字 |
| 🧠 **记忆与偏好** | 对话历史滚动 200 条,用户偏好持久化,清空一键搞定 |
| 🔍 **联网搜索** | DuckDuckGo HTML 抓取,关键词触发,搜索结果注入到 prompt |
| 🪟 **开机自启** | Windows `HKCU\...\Run` 注册表,macOS `LaunchAgent`,Linux `.desktop` autostart |
| 🟢 **开机自启 / 状态点** | 模型按钮旁的绿/黄/红状态点:idle / busy / error |
| 📝 **Markdown 渲染** | 粗体 / 斜体 / 行内代码 / 代码块 / 标题 / 列表 / 引用 / 链接,代码块带等宽字体 + 暗背景 |
| ⌨️ **斜杠指令** | `/help` `/clear` `/settings` `/提示词` `/model` `/exit` —— 边输入边自动补全 |
| 🎨 **精心打磨的 UI** | Frameless 自定义标题栏、OutQuart 缓动动画、fade + slide、智能滚屏(用户离开底部不自动跟) |
| 🌐 **跨平台** | Windows / macOS / Linux 全平台 PyQt5 跑得起来 |

---

## 📸 截图 Screenshots

> 运行时截图,所有 UI 元素都真实可见。

<details>
<summary><b>主界面 + Markdown 渲染</b></summary>

```
┌─────────────────────────────────────────────┐
│ 你 13:14                                    │
│ 写一个斐波那契函数                          │
│                                             │
│ 助手 13:14                                  │
│ 好的,这里有**迭代**版本:                    │
│                                             │
│ ┌─────────────────────────────────────────┐ │
│ │ def fib(n):                             │ │
│ │     a, b = 0, 1                         │ │
│ │     for _ in range(n):                  │ │
│ │         a, b = b, a+b                   │ │
│ │     return a                            │ │
│ └─────────────────────────────────────────┘ │
│                                             │
│ • 时间: O(n)                                │
│ • 空间: O(1)                                │
├─────────────────────────────────────────────┤
│ 输入消息… (输入 / 唤起命令)                 │
│ + ⟳  ● deepseek-chat ▾        ↑           │
└─────────────────────────────────────────────┘
```

</details>

<details>
<summary><b>设置对话框</b></summary>

- Frameless 自定义标题栏(设置 + ✕ 关闭按钮)
- 弹出位置:跟随鼠标 / 底部居中 / 记住上次位置
- 界面缩放:紧凑 / 默认 / 舒适 / 放大
- 模型提供方 + 模型 + Base URL + API Key(每个 provider 独立存 key)
- 开机自启 + 清空记忆与对话

</details>

---

## 🚀 快速开始 Quick Start

### 1. 下载预编译版本(推荐)

去 [Releases](https://github.com/zhaozzh2013/flashai/releases) 下载对应平台的压缩包:
- Windows: `FlashAI-v0.01-windows.zip` → 解压 → 双击 `智能助手.exe`
- macOS: `FlashAI-v0.01-macos.dmg` → 拖入 Applications
- Linux: `FlashAI-v0.01-linux.tar.gz` → 解压 → `./智能助手`

### 2. 从源码运行

需要 **Python 3.10+**(3.14 也跑得起来,只是 PyQt5 5.15.11 需要一个小补丁,已在 `app.py` 处理)。

```bash
# 克隆
git clone https://github.com/zhaozzh2013/flashai.git
cd flashai

# 创建虚拟环境
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 跑起来
python app.py
```

> 第一次跑会弹一个 `未配置 API Key` 的提示 —— 打开设置,把任一提供方的 Key 填进去即可。

### 3. 配 API Key

打开设置 (点 `+` 按钮 → 设置,或输入 `/settings`),在 **API Key** 那一行粘贴你的 key。
每个提供方都用自己的 key,切换时不需要重复填。

也可以用环境变量兜底(legacy):
```bash
# .env 文件
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

---

## 🎮 使用 Usage

| 操作 | 效果 |
|---|---|
| **三连空格** | 唤起 / 隐藏窗口(1.2 s 窗口内) |
| **Esc** | 隐藏窗口 |
| **Enter** | 发送消息 |
| **Shift + Enter** | 输入框里换行 |
| **输入 `/`** | 弹出指令补全 |
| **点 `+`** | 弹出"更多"菜单(设置/提示词/退出) |
| **点 `⟳`** | 清空当前对话 |
| **点模型按钮** | 切换当前提供方下的模型 |
| **拖动窗口** | 移动(在"记住上次位置"模式下会持久化) |

### 指令 Commands

| 指令 | 作用 |
|---|---|
| `/help` | 显示帮助 |
| `/clear` | 清空对话(记忆 + 偏好) |
| `/settings` | 打开设置 |
| `/提示词` | 更改系统提示词(偏好) |
| `/model [名称]` | 查看或切换模型;例:`/model gpt-4o` |
| `/exit` | 关闭助手 |

### 联网搜索

当消息含以下关键词时,会自动搜索并把结果注入到 prompt:
`搜索 搜一下 查一下 百度 google 谷歌 最新 今天 昨天 今年 新闻 现在`

---

## 🏗️ 自己编译 Build

### Windows

```cmd
pip install pyinstaller
pyinstaller flashai.spec
:: 产物在 dist\智能助手\
```

### macOS / Linux

```bash
chmod +x build.sh
./build.sh       # 调 PyInstaller 打 .app / 可执行文件
# 产物在 dist/
```

### 多平台 CI

推一个 tag 就自动出 3 个平台的 release:

```bash
git tag v0.01
git push origin v0.01
```

GitHub Actions 会跑 `.github/workflows/release.yml`,在 Windows / macOS / Ubuntu runner 上分别构建,产物自动上传到 Release。

---

## 🧩 架构 Architecture

```
flashai/
├── app.py              # 入口:启动 GUI + 全局快捷键
├── ui.py               # 主窗口 MainApp + 设置对话框 SettingsDialog
├── md.py               # 轻量 Markdown → HTML 渲染器
├── agent.py            # 与模型对话:SSE 流式 (OpenAI + Anthropic 双协议)
├── config.py           # 5 家提供方配置 + base_url / 模型列表 / 帮助文案
├── settings.py         # 持久化 (settings.json):提供方 / 模型 / Key / 位置 / 缩放
├── memory.py           # 短期对话历史 + 长期偏好
├── web_search.py       # DuckDuckGo HTML 抓取
├── hotkey.py           # pynput 三连空格监听
├── autostart.py        # 开机自启 (winreg / LaunchAgent / .desktop)
├── requirements.txt
└── flashai.spec        # PyInstaller 打包配置
```

**数据流(一次对话):**
1. 用户输入 → `MainApp._on_send`
2. `_append_bubble("你", text)` 渲染并展示用户气泡
3. `agent.chat(text, on_chunk=...)` 在后台线程跑 SSE
4. 每个 chunk → `sig_chunk.emit(chunk)` → 主线程 `_on_chunk` 触发 `_update_stream_body`
5. `_update_stream_body` 用 `md.render(self._stream_text)` 重新渲染气泡 body(支持 Markdown)
6. 结束 → `sig_reply.emit(full)` → `_on_reply` finalize

---

## 🛠️ 故障排查 Troubleshooting

### 启动报错 "could not find Qt platform plugin windows"
PyQt5 5.15.11 + Python 3.14 有兼容问题,本项目已在 `app.py` 用 `_fix_pyqt5_plugins()` 修复,会自动定位 `PyQt5/Qt5/plugins/platforms` 并加进 `QT_QPA_PLATFORM_PLUGIN_PATH`。如果还报错:
```bash
pip install --upgrade PyQt5
```

### 三连空格不响应
- 检查是否有其他应用占用键盘钩子
- 在设置里切换位置模式
- 看 `%APPDATA%\智能助手\settings.json` 确认 `position_mode` 字段存在

### 流式输出卡住 / 中断
- API 提供方限流 → 稍等再试
- 看终端日志(命令行 `python app.py` 跑起来会有 INFO 输出)

### 卸载
- 删整个文件夹
- Windows: 删 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 里的 `SmartAssistant` 项
- 删 `%APPDATA%\智能助手\` 目录(对话记忆)

---

## 📝 License

[MIT](LICENSE) © 2026 zhaozzh2013

---

## 🙏 致谢

- 灵感来自 Claude / Raycast / Spotlight
- PyQt5 / pynput / requests
