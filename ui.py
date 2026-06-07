"""
PyQt5 界面：扁平化悬浮输入条，模型提供方切换 + 流式输出。

行为约定：
- 默认隐藏
- 三连空格触发：按 position_mode 弹出（默认 follow_mouse）
- 淡入 + 向上滑入（220ms）；淡出 + 向下滑出（160ms）
- 首次发送后窗口向上生长，露出历史对话区
- Enter 发送，Shift+Enter 换行
- Esc 隐藏；失焦 150ms 后自动隐藏（子对话框开着时不躲）
- 助手回复走流式（SSE），逐 chunk 追加到气泡
"""
from __future__ import annotations

import threading
from datetime import datetime

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import (
    Qt, QEvent, QTimer, QRect, QPropertyAnimation,
    QEasingCurve, QParallelAnimationGroup, QAbstractAnimation,
    pyqtSignal, pyqtSlot,
)
from PyQt5.QtGui import QCursor, QGuiApplication, QTextCursor

import agent
import autostart
import config
import md
import memory
import settings


# ---------- 字号 / 尺寸 ----------
def _s(base: float) -> int:
    scale = float(settings.get("ui_scale", 1.2) or 1.2)
    return max(8, int(round(base * scale)))


# ---------- 字体栈：优先苹方/鸿蒙/思源黑体，回退系统 ----------
_FONT_STACK = (
    '"HarmonyOS Sans SC", "Source Han Sans CN", "Noto Sans CJK SC", '
    '"PingFang SC", "Microsoft YaHei UI", "Microsoft YaHei", '
    '"Segoe UI", system-ui, sans-serif'
)


# ---------- 样式（扁平化、无圆角边框） ----------
def _build_style() -> str:
    s = _s
    f = _FONT_STACK
    return f"""
* {{
    font-family: {f};
    font-weight: 450;
    letter-spacing: 0.1px;
}}
QWidget#container {{
    background: #1a1b1e;
    border: 1px solid #2a2b30;
    border-radius: 6px;
}}
QTextEdit#history {{
    background: transparent;
    color: #d6d6d6;
    border: none;
    font-size: {s(15)}px;
    padding: 6px 8px 4px 8px;
    line-height: 1.7;
    selection-background-color: #3a4255;
}}
QTextEdit#input {{
    background: #232427;
    color: #ececec;
    border: 1px solid #2e2f34;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: {s(16)}px;
    selection-background-color: #3a4255;
}}
QTextEdit#input:focus {{
    border-color: #5a6480;
    background: #26272a;
}}
QTextEdit#input::placeholder {{ color: #6b6e75; }}
QTextEdit#input QScrollBar:vertical {{
    background: transparent; width: 6px; margin: 4px 2px;
}}
QTextEdit#input QScrollBar::handle:vertical {{
    background: #44464b; border-radius: 3px; min-height: 20px;
}}
QTextEdit#input QScrollBar::add-line:vertical,
QTextEdit#input QScrollBar::sub-line:vertical {{ height: 0; }}
QPushButton {{
    color: #a8acb3; background: transparent; border: none;
    font-size: {s(16)}px; padding: 0; font-weight: 500;
}}
QPushButton:hover {{ color: #ffffff; }}
QPushButton#iconbtn {{
    font-size: {s(20)}px; border-radius: 4px;
    min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
}}
QPushButton#iconbtn:hover {{ background: #2a2b30; color: #ffffff; }}
QPushButton#iconbtn:pressed {{ background: #34353a; }}
QLabel#status_dot {{
    color: #7ee787; font-size: 11px; background: transparent;
    padding: 0; margin: 0 2px 0 4px; border: none;
}}
QListWidget#cmdpopup {{
    background: #232427; color: #d6d6d6;
    border: 1px solid #363a40; border-radius: 6px;
    padding: 4px; outline: 0;
    font-size: 13px;
}}
QListWidget#cmdpopup::item {{
    padding: 6px 10px; border-radius: 4px;
}}
QListWidget#cmdpopup::item:selected {{
    background: #313438; color: #ffffff;
}}
QPushButton#ctxbtn {{
    font-size: {s(12)}px; color: #b6bac1;
    padding: 6px 12px; border-radius: 4px;
    font-weight: 500;
}}
QPushButton#ctxbtn:hover {{ background: #2a2b30; color: #ffffff; }}
QPushButton#ctxbtn:pressed {{ background: #34353a; }}
QPushButton#send {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #d8d9dc);
    color: #1a1b1e; border: none; border-radius: 4px;
    min-width: 34px; max-width: 34px; min-height: 34px; max-height: 34px;
    font-size: {s(17)}px; font-weight: 700;
}}
QPushButton#send:hover {{ background: #ffffff; }}
QPushButton#send:pressed {{ background: #c8c9cc; }}
QPushButton#send:disabled {{ background: #2e2f34; color: #6c6f76; }}
QMenu {{
    background: #232427; color: #d6d6d6;
    border: 1px solid #363a40; border-radius: 6px; padding: 6px;
    font-size: {s(13)}px;
}}
QMenu::item {{ padding: 6px 22px; border-radius: 4px; }}
QMenu::item:selected {{ background: #313438; color: #ffffff; }}
QMenu::item:checked {{ color: #7da7ff; }}
QMenu::separator {{ height: 1px; background: #363a40; margin: 6px 4px; }}
QMenu::right-arrow {{ image: none; }}
QMenu::indicator {{ width: 14px; height: 14px; }}

/* 设置对话框 */
QDialog {{ background: #1a1b1e; color: #d6d6d6; border: 1px solid #2a2b30; border-radius: 6px; }}
QWidget#dlg_titlebar {{
    background: #1a1b1e;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    border-bottom: 1px solid #2a2b30;
}}
QWidget#dlg_body {{ background: #1a1b1e; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }}
QPushButton#dlg_close {{
    background: transparent; color: #8a8d94; border: none;
    border-radius: 4px; font-size: 14px; font-weight: 700;
    padding: 0; min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px;
}}
QPushButton#dlg_close:hover {{ background: #3a1f1f; color: #ff8a8a; }}
QPushButton#dlg_close:pressed {{ background: #5a2828; color: #ffb0b0; }}
QLabel {{ color: #a8acb3; font-size: {s(13)}px; }}
QLabel#title {{ color: #ffffff; font-size: {s(15)}px; font-weight: 600; }}
QLabel#hint {{ color: #6f7279; font-size: {s(11)}px; }}
QLineEdit, QComboBox {{
    background: #232427; color: #ececec;
    border: 1px solid #363a40; border-radius: 4px;
    padding: 8px 12px; font-size: {s(13)}px;
    selection-background-color: #3a4255;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: #5a6480; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: #232427; color: #ececec;
    border: 1px solid #363a40; selection-background-color: #313438;
    padding: 4px;
}}
QCheckBox {{ color: #d6d6d6; font-size: {s(13)}px; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px; border: 1px solid #44464b;
    border-radius: 3px; background: #232427;
}}
QCheckBox::indicator:checked {{ background: #5a6480; border-color: #5a6480; }}
QPushButton#dialogbtn {{
    background: #232427; color: #d6d6d6;
    border: 1px solid #363a40; border-radius: 4px;
    padding: 8px 18px; font-size: {s(13)}px; font-weight: 500;
}}
QPushButton#dialogbtn:hover {{ background: #2e2f34; color: #ffffff; }}
QPushButton#primary {{
    background: #5a6480; color: #ffffff; border: none; border-radius: 4px;
    padding: 8px 20px; font-size: {s(13)}px; font-weight: 600;
}}
QPushButton#primary:hover {{ background: #6a7595; }}
QPushButton#primary:pressed {{ background: #4a5470; }}
QPushButton#danger {{
    background: transparent; color: #e58a8a;
    border: 1px solid #5a3030; border-radius: 4px;
    padding: 8px 16px; font-size: {s(13)}px;
}}
QPushButton#danger:hover {{ background: #2a1818; }}
"""


# ---------- 斜杠指令 ----------
_COMMANDS = [
    ("/help", "显示帮助"),
    ("/clear", "清空当前对话"),
    ("/settings", "打开设置"),
    ("/提示词", "更改系统提示词"),
    ("/model", "查看或切换模型（可加模型名）"),
    ("/exit", "关闭助手"),
]

_HELP_TEXT = """可用指令：

  /help      显示本帮助
  /clear     清空当前对话(记忆 + 偏好)
  /settings  打开设置
  /提示词    更改系统提示词(偏好)
  /model     查看或切换模型;例:/model gpt-4o
  /exit      关闭助手

直接输入文字即可与 AI 对话。"""


# ---------- 输入框事件过滤器 ----------
class _InputKeyFilter(QtCore.QObject):
    def __init__(self, on_send):
        super().__init__()
        self._on_send = on_send

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() & Qt.ShiftModifier:
                    return False
                self._on_send()
                return True
        return False


# ---------- 斜杠指令自动补全 ----------
class _CommandPopup(QtWidgets.QListWidget):
    def __init__(self, parent_app: "MainApp"):
        super().__init__(parent_app)
        self._app = parent_app
        self.setObjectName("cmdpopup")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setMinimumWidth(280)
        self.setMaximumHeight(220)
        for cmd, desc in _COMMANDS:
            item = QtWidgets.QListWidgetItem(f"{cmd}   {desc}")
            item.setData(Qt.UserRole, cmd)
            self.addItem(item)
        self.itemClicked.connect(self._on_clicked)

    def filter(self, prefix: str) -> None:
        prefix = prefix.lower().lstrip("/")
        self.clear()
        any_match = False
        for cmd, desc in _COMMANDS:
            short = cmd.lstrip("/").lower()
            if not prefix or short.startswith(prefix):
                self.addItem(QtWidgets.QListWidgetItem(f"{cmd}   {desc}"))
                any_match = True
        if any_match:
            self.setCurrentRow(0)
            self.show()
        else:
            self.hide()

    def _on_clicked(self, item: QtWidgets.QListWidgetItem) -> None:
        self._app.apply_command_suggestion(item.text().split()[0])
        self.hide()


# ---------- 设置对话框 ----------
class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(580)
        # 跟主窗口一样:FramelessWindowHint,自己画标题栏和关闭按钮
        # (主窗口能隐藏 Win11 边框就是靠这个 flag)
        self.setWindowFlags(
            Qt.Dialog | Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self._drag_pos: QtCore.QPoint | None = None
        self._build()
        self._load()
        # 入场淡入
        self._fx = QtWidgets.QGraphicsOpacityEffect(self)
        self._fx.setOpacity(0.0)
        self.setGraphicsEffect(self._fx)
        QTimer.singleShot(0, self._animate_in)

    def _animate_in(self) -> None:
        anim = QPropertyAnimation(self._fx, b"opacity")
        anim.setDuration(180)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    # 让标题栏可以拖动
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and event.y() < 44:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _build(self):
        # 自定义标题栏 + 内容区(主窗口的 FramelessWindowHint 同款做法)
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏
        title_bar = QtWidgets.QWidget()
        title_bar.setObjectName("dlg_titlebar")
        title_bar.setFixedHeight(40)
        tb = QtWidgets.QHBoxLayout(title_bar)
        tb.setContentsMargins(16, 0, 6, 0)
        tb.setSpacing(0)
        title = QtWidgets.QLabel("设置")
        title.setObjectName("title")
        tb.addWidget(title)
        tb.addStretch(1)
        self.btn_close = QtWidgets.QPushButton("✕")
        self.btn_close.setObjectName("dlg_close")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.clicked.connect(self.reject)
        tb.addWidget(self.btn_close)
        outer.addWidget(title_bar)

        # 内容容器(给一个看起来像 dialog body 的背景)
        body = QtWidgets.QWidget()
        body.setObjectName("dlg_body")
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(14)
        outer.addWidget(body, 1)

        # 弹出位置
        self.position_combo = QtWidgets.QComboBox()
        self.position_combo.addItem("跟随鼠标", "follow_mouse")
        self.position_combo.addItem("底部居中", "bottom_center")
        self.position_combo.addItem("记住上次位置", "remember")
        self._form_row(layout, "弹出位置", self.position_combo)

        # 界面缩放
        self.scale_combo = QtWidgets.QComboBox()
        for label, val in [("紧凑", 0.9), ("默认", 1.0), ("舒适", 1.1), ("放大", 1.2)]:
            self.scale_combo.addItem(label, val)
        self._form_row(layout, "界面缩放", self.scale_combo)

        layout.addWidget(self._hline())

        # 模型提供方
        api_title = QtWidgets.QLabel("模型提供方")
        api_title.setObjectName("title")
        layout.addWidget(api_title)

        self.provider_combo = QtWidgets.QComboBox()
        for key in config.PROVIDER_ORDER:
            info = config.PROVIDERS[key]
            self.provider_combo.addItem(info["name"], key)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_change)
        self._form_row(layout, "提供方", self.provider_combo)

        # 模型(只列当前提供方的模型)
        self.model_combo = QtWidgets.QComboBox()
        self._form_row(layout, "模型", self.model_combo)

        # 自定义 Base URL + Key
        self.baseurl_edit = QtWidgets.QLineEdit()
        self.baseurl_edit.setPlaceholderText("https://api.example.com/v1")
        self._form_row(layout, "Base URL", self.baseurl_edit)

        # API Key
        self.key_edit = QtWidgets.QLineEdit()
        self.key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self._form_row(layout, "API Key", self.key_edit)

        self.key_hint = QtWidgets.QLabel("")
        self.key_hint.setObjectName("hint")
        self.key_hint.setWordWrap(True)
        layout.addWidget(self.key_hint)

        # 自启
        self.autostart_chk = QtWidgets.QCheckBox("开机自启")
        layout.addWidget(self.autostart_chk)

        layout.addWidget(self._hline())

        # 危险操作
        danger = QtWidgets.QHBoxLayout()
        self.clear_btn = QtWidgets.QPushButton("清空记忆与对话")
        self.clear_btn.setObjectName("danger")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._on_clear)
        danger.addWidget(self.clear_btn)
        danger.addStretch(1)
        layout.addLayout(danger)

        # 底部按钮
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        cancel_btn = QtWidgets.QPushButton("取消")
        cancel_btn.setObjectName("dialogbtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = QtWidgets.QPushButton("保存")
        ok_btn.setObjectName("primary")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)

    def _form_row(self, parent_layout, label, widget):
        row = QtWidgets.QHBoxLayout()
        l = QtWidgets.QLabel(label)
        l.setFixedWidth(80)
        row.addWidget(l, 0)
        row.addWidget(widget, 1)
        parent_layout.addLayout(row)

    def _hline(self):
        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("background:#2c2d31;")
        line.setFixedHeight(1)
        return line

    def _on_provider_change(self, _idx: int) -> None:
        # 切提供方时刷新模型列表
        self._refresh_model_combo()

    def _refresh_model_combo(self) -> None:
        key = self.provider_combo.currentData()
        info = config.PROVIDERS.get(key, {})
        models = list(info.get("models", []))
        default = info.get("default_model", "")

        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for m in models:
            self.model_combo.addItem(m, m)
        # 默认选中 provider 的 default_model
        if default:
            idx = self.model_combo.findData(default)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        self.model_combo.blockSignals(False)

        # base_url: 优先用 settings 里的 base_urls[provider],否则用 provider 默认
        base_urls = settings.get("base_urls", {}) or {}
        if isinstance(base_urls, dict) and base_urls.get(key):
            self.baseurl_edit.setText(str(base_urls[key]))
        else:
            self.baseurl_edit.setPlaceholderText(str(info.get("base_url", "")))

        # key_hint
        self.key_hint.setText(info.get("key_hint", ""))
        # 当前提供方已存的 key
        keys = settings.get("api_keys", {}) or {}
        if isinstance(keys, dict):
            self.key_edit.setText(str(keys.get(key, "") or ""))
        else:
            self.key_edit.setText("")

    def _on_model_combo_change(self, _idx: int) -> None:
        pass

    def _load(self) -> None:
        s = settings.load()
        # position / scale
        for i in range(self.position_combo.count()):
            if self.position_combo.itemData(i) == s.get("position_mode", "follow_mouse"):
                self.position_combo.setCurrentIndex(i)
                break
        for i in range(self.scale_combo.count()):
            if abs(self.scale_combo.itemData(i) - float(s.get("ui_scale", 1.2))) < 0.01:
                self.scale_combo.setCurrentIndex(i)
                break
        # provider
        cur_provider = s.get("provider", "openai")
        for i in range(self.provider_combo.count()):
            if self.provider_combo.itemData(i) == cur_provider:
                self.provider_combo.setCurrentIndex(i)
                break
        # 模型 + key 依赖 _refresh_model_combo
        self._refresh_model_combo()
        # 自启
        self.autostart_chk.setChecked(autostart.is_enabled())

    def _on_accept(self) -> None:
        s = settings.load()
        s["position_mode"] = self.position_combo.currentData()
        s["ui_scale"] = self.scale_combo.currentData()
        s["provider"] = self.provider_combo.currentData()

        # 模型(只可能是下拉里选出来的)
        m_data = self.model_combo.currentData()
        if m_data:
            s["model"] = m_data
        else:
            s["model"] = config.PROVIDERS[s["provider"]]["default_model"]

        # Base URL: 如果用户改了,就存到 base_urls[provider];空着就清掉,fallback 到 provider 默认
        base_urls = dict(s.get("base_urls", {}) or {})
        url = self.baseurl_edit.text().strip()
        if url:
            base_urls[s["provider"]] = url
        else:
            base_urls.pop(s["provider"], None)
        s["base_urls"] = base_urls

        # API Key
        keys = dict(s.get("api_keys", {}) or {})
        keys[s["provider"]] = self.key_edit.text().strip()
        s["api_keys"] = keys

        settings.save(s)

        # 同步自启
        if self.autostart_chk.isChecked() and not autostart.is_enabled():
            autostart.enable()
        elif not self.autostart_chk.isChecked() and autostart.is_enabled():
            autostart.disable()

        self.accept()

    def _on_clear(self):
        ret = QtWidgets.QMessageBox.question(
            self, "确认", "清空所有对话历史和偏好？\n此操作不可恢复。",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if ret == QtWidgets.QMessageBox.Yes:
            memory.reset_all()
            QtWidgets.QMessageBox.information(self, "完成", "已清空所有记忆")


# ---------- 主窗口 ----------
class MainApp(QtWidgets.QWidget):
    sig_chunk = pyqtSignal(str)         # 流式 chunk（后台线程 -> 主线程）
    sig_reply = pyqtSignal(str)         # 流式结束
    sig_error = pyqtSignal(str)

    COLLAPSED_H = 158
    EXPANDED_H = 560
    WIDTH = 820
    SCREEN_MARGIN = 16
    ANIM_SHOW_MS = 280
    ANIM_HIDE_MS = 200
    ANIM_EXPAND_MS = 280
    SLIDE_PX = 24
    INPUT_H = 76
    ICON_BTN = 36

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(_build_style())

        self._expanded = False
        self._anim: QParallelAnimationGroup | None = None
        self._geom_anim: QPropertyAnimation | None = None
        self._fx: QtWidgets.QGraphicsOpacityEffect | None = None
        self._child_dialog_open = False

        # 流式相关
        self._stream_active = False
        self._stream_cursor: QTextCursor | None = None
        self._stream_text = ""
        self._stream_body_start: int | None = None
        self._stream_body_end: int | None = None

        self._build_ui()
        self._wire_signals()

        # 默认收起(只显示输入栏),_set_expanded(True) 时才展开历史区
        self.history.hide()
        self.history.setMaximumHeight(0)
        self.history.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Ignored,
        )
        # 用 layout 的 sizeHint 作为窗口的初始尺寸,避免 640x480 默认值
        self.resize(self.WIDTH, self.layout().sizeHint().height())
        self.hide()

    # ---------- 构建 ----------
    def _build_ui(self) -> None:
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.container = QtWidgets.QWidget()
        self.container.setObjectName("container")
        outer.addWidget(self.container)

        self._fx = QtWidgets.QGraphicsOpacityEffect(self.container)
        self._fx.setOpacity(1.0)
        self.container.setGraphicsEffect(self._fx)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 历史区
        self.history = QtWidgets.QTextEdit()
        self.history.setObjectName("history")
        self.history.setReadOnly(True)
        self.history.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # 关键:关掉自动 Markdown/有序列表格式化,避免 "1. " "2. " 被当成 ol
        self.history.setAutoFormatting(QtWidgets.QTextEdit.AutoNone)
        # 收起时高度为 0,不让它撑大窗口 sizeHint
        self.history.setMinimumHeight(0)
        self.history.setMaximumHeight(0)
        self.history.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Ignored,
        )
        layout.addWidget(self.history, stretch=1)

        # 输入框
        self.input = QtWidgets.QTextEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("输入消息…（输入 / 唤起命令）")
        self.input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.input.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input.setFixedHeight(self.INPUT_H)
        layout.addWidget(self.input)

        # 底栏
        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(6)
        bottom.setContentsMargins(4, 0, 4, 0)

        self.btn_attach = QtWidgets.QPushButton("+")
        self.btn_attach.setObjectName("iconbtn")
        self.btn_attach.setCursor(Qt.PointingHandCursor)
        self.btn_attach.setToolTip("更多")
        self.btn_attach.clicked.connect(self._on_attach)

        self.btn_switch = QtWidgets.QPushButton("⟳")
        self.btn_switch.setObjectName("iconbtn")
        self.btn_switch.setCursor(Qt.PointingHandCursor)
        self.btn_switch.setToolTip("清空当前对话")
        self.btn_switch.clicked.connect(self._on_clear)

        bottom.addWidget(self.btn_attach)
        bottom.addWidget(self.btn_switch)
        bottom.addStretch(1)

        # 状态点
        self.status_dot = QtWidgets.QLabel("●")
        self.status_dot.setObjectName("status_dot")
        self.status_dot.setFixedWidth(14)
        self.status_dot.setAlignment(Qt.AlignCenter)
        self.status_dot.setToolTip("就绪")

        self.btn_ctx = QtWidgets.QPushButton()
        self.btn_ctx.setObjectName("ctxbtn")
        self.btn_ctx.setCursor(Qt.PointingHandCursor)
        self.btn_ctx.clicked.connect(self._on_ctx_menu)
        self._refresh_model_label()

        self.btn_send = QtWidgets.QPushButton("↑")
        self.btn_send.setObjectName("send")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self._on_send)

        bottom.addWidget(self.status_dot)
        bottom.addWidget(self.btn_ctx)
        bottom.addSpacing(4)
        bottom.addWidget(self.btn_send)
        layout.addLayout(bottom)

        self._key_filter = _InputKeyFilter(self._on_send)
        self.input.installEventFilter(self._key_filter)

        # 斜杠指令自动补全
        self._cmd_popup = _CommandPopup(self)
        self._cmd_popup.hide()
        self.input.textChanged.connect(self._on_input_changed)

    def _wire_signals(self) -> None:
        self.sig_chunk.connect(self._on_chunk)
        self.sig_reply.connect(self._on_reply)
        self.sig_error.connect(self._on_error)

    # ---------- 斜杠指令补全 ----------
    def _on_input_changed(self) -> None:
        text = self.input.toPlainText()
        # 只在第一行 / 只有一个 / 块 触发补全
        if "\n" in text:
            self._cmd_popup.hide()
            return
        if text.startswith("/") and " " not in text and "\t" not in text:
            self._cmd_popup.filter(text)
            # 定位:输入框上方,贴左边
            if not self._cmd_popup.isVisible():
                return
            self._cmd_popup.adjustSize()
            g = self.input.geometry()
            top_left = self.input.mapToGlobal(QtCore.QPoint(g.left(), g.top()))
            x = top_left.x()
            y = top_left.y() - self._cmd_popup.height() - 4
            self._cmd_popup.move(x, y)
            self._cmd_popup.raise_()
        else:
            self._cmd_popup.hide()

    def apply_command_suggestion(self, cmd: str) -> None:
        """点击补全项:把当前 /xxx 替换为 cmd + 空格"""
        self.input.setPlainText(f"{cmd} ")
        cursor = self.input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input.setTextCursor(cursor)

    # ---------- 模型 / 提供方 ----------
    def _refresh_model_label(self) -> None:
        prov = config.current_provider()
        m = config.current_model()
        # 主按钮只显示模型名（提供方在菜单里一目了然）
        short = m if len(m) <= 18 else m[:16] + "…"
        self.btn_ctx.setText(f"{short} ▾")
        self.btn_ctx.setToolTip(f"{prov['name']} · {m}")

    def _on_ctx_menu(self) -> None:
        """下拉只显示当前提供方的模型,点击切换;不放其他任何项。"""
        menu = QtWidgets.QMenu(self)
        cur_provider_key = config.current_provider_key()
        cur_model = config.current_model()
        info = config.PROVIDERS[cur_provider_key]
        for m in info["models"]:
            act = menu.addAction(m)
            act.setCheckable(True)
            act.setChecked(m == cur_model)
            act.triggered.connect(
                lambda checked, model=m: self._switch_model(cur_provider_key, model)
            )

        menu.exec_(
            self.btn_ctx.mapToGlobal(QtCore.QPoint(0, self.btn_ctx.height()))
        )

    def _switch_model(self, provider_key: str, model_name: str) -> None:
        settings.set_value("provider", provider_key)
        settings.set_value("model", model_name)
        self._refresh_model_label()
        self._append_bubble(
            "系统",
            f"已切换：{config.PROVIDERS[provider_key]['name']} · {model_name}",
        )

    def _set_custom_model(self) -> None:
        cur = config.current_model()
        text, ok = QtWidgets.QInputDialog.getText(
            self, "自定义模型", "输入模型名称（确定后会切到当前提供方）：",
            text=cur,
        )
        if ok and text.strip():
            settings.set_value("model", text.strip())
            self._refresh_model_label()
            self._append_bubble("系统", f"已切换到自定义模型: {text.strip()}")

    # ---------- 几何 ----------
    def _current_screen_geo(self) -> QtCore.QRect | None:
        pos = QCursor.pos()
        screen = QGuiApplication.screenAt(pos) or QtWidgets.QApplication.primaryScreen()
        return screen.availableGeometry() if screen else None

    def _compute_geometry(self, expanded: bool) -> QRect:
        mode = settings.get("position_mode", "follow_mouse")
        h = self.EXPANDED_H if expanded else self.COLLAPSED_H
        geo = self._current_screen_geo()
        if geo is None:
            return QRect(200, 200, self.WIDTH, h)

        if mode == "bottom_center":
            x = geo.left() + (geo.width() - self.WIDTH) // 2
            y = geo.bottom() - self.SCREEN_MARGIN - h
            return QRect(x, y, self.WIDTH, h)

        if mode == "remember":
            last = settings.get("last_pos", None)
            if isinstance(last, (list, tuple)) and len(last) == 2:
                x, y = int(last[0]), int(last[1])
                # 限制在当前屏幕内
                m = 12
                x = max(geo.left() + m, min(x, geo.right() - m - self.WIDTH))
                y = max(geo.top() + m, min(y, geo.bottom() - m - h))
                return QRect(x, y, self.WIDTH, h)
            # 没有上次位置,回退到跟随鼠标
            mode = "follow_mouse"

        m = 12
        pos = QCursor.pos()
        y = pos.y() - 12
        if y + h > geo.bottom() - m:
            y = pos.y() - h + 12
        if y < geo.top() + m:
            y = geo.top() + m
        x = pos.x() - self.WIDTH // 2
        if x < geo.left() + m:
            x = geo.left() + m
        elif x + self.WIDTH > geo.right() - m:
            x = geo.right() - m - self.WIDTH
        return QRect(x, y, self.WIDTH, h)

    def _save_position(self) -> None:
        """记住当前窗口位置(给 position_mode=remember 用)"""
        if settings.get("position_mode", "follow_mouse") != "remember":
            return
        g = self.geometry()
        try:
            s = settings.load()
            s["last_pos"] = [g.x(), g.y()]
            settings.save(s)
        except Exception:
            pass

    # ---------- 动画 ----------
    def _cancel_anim(self) -> None:
        if self._anim and self._anim.state() == QAbstractAnimation.Running:
            self._anim.stop()
        self._anim = None

    def _start_show(self, target: QRect, start: QRect) -> None:
        self._cancel_anim()
        self._fx.setOpacity(0.0)
        self.setGeometry(start)
        self.show()
        self.raise_()
        self.activateWindow()

        self._anim = QParallelAnimationGroup(self)
        geom = QPropertyAnimation(self, b"geometry")
        geom.setDuration(self.ANIM_SHOW_MS)
        geom.setStartValue(start)
        geom.setEndValue(target)
        geom.setEasingCurve(QEasingCurve.OutQuart)

        fade = QPropertyAnimation(self._fx, b"opacity")
        fade.setDuration(self.ANIM_SHOW_MS)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutQuart)

        self._anim.addAnimation(geom)
        self._anim.addAnimation(fade)
        self._anim.start()

    def _start_hide(self) -> None:
        self._cancel_anim()
        cur = self.geometry()
        end = QRect(cur.x(), cur.y() + self.SLIDE_PX, cur.width(), cur.height())

        self._anim = QParallelAnimationGroup(self)
        geom = QPropertyAnimation(self, b"geometry")
        geom.setDuration(self.ANIM_HIDE_MS)
        geom.setStartValue(cur)
        geom.setEndValue(end)
        geom.setEasingCurve(QEasingCurve.InQuart)

        fade = QPropertyAnimation(self._fx, b"opacity")
        fade.setDuration(self.ANIM_HIDE_MS)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.InQuart)

        self._anim.addAnimation(geom)
        self._anim.addAnimation(fade)
        self._anim.finished.connect(self._on_hide_done)
        self._anim.start()

    def _on_hide_done(self) -> None:
        super().hide()
        self._fx.setOpacity(1.0)
        if self._expanded:
            self._expanded = False
            self.history.setVisible(False)
        self._anim = None

    def _animate_geometry(self, end: QRect, duration: int) -> None:
        if self._geom_anim and self._geom_anim.state() == QAbstractAnimation.Running:
            self._geom_anim.stop()
        self._geom_anim = QPropertyAnimation(self, b"geometry")
        self._geom_anim.setDuration(duration)
        self._geom_anim.setStartValue(self.geometry())
        self._geom_anim.setEndValue(end)
        self._geom_anim.setEasingCurve(QEasingCurve.OutQuart)
        self._geom_anim.start()

    # ---------- 显示 / 隐藏 ----------
    @pyqtSlot()
    def show_at_cursor(self) -> None:
        target = self._compute_geometry(self._expanded)
        start = QRect(target.x(), target.y() + self.SLIDE_PX, target.width(), target.height())
        self._start_show(target, start)
        self.input.setFocus()
        cursor = self.input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.input.setTextCursor(cursor)

    def hide(self) -> None:  # type: ignore[override]
        # 关之前先记下位置(给 position_mode=remember 用)
        self._save_position()
        self._start_hide()

    def moveEvent(self, event) -> None:  # noqa: N802
        super().moveEvent(event)
        # 拖动时持续记(限频:QTimer 单次)
        if not hasattr(self, "_save_pos_timer") or self._save_pos_timer is None:
            self._save_pos_timer = QTimer(self)
            self._save_pos_timer.setSingleShot(True)
            self._save_pos_timer.setInterval(400)
            self._save_pos_timer.timeout.connect(self._save_position)
        self._save_pos_timer.start()

    def _set_expanded(self, expanded: bool, animated: bool = True) -> None:
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.history.setVisible(expanded)
        # 同步 history 的最大高度,让 layout sizeHint 跟着切换
        if expanded:
            self.history.setMaximumHeight(16777215)
            self.history.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Expanding,
            )
        else:
            self.history.setMaximumHeight(0)
            self.history.setSizePolicy(
                QtWidgets.QSizePolicy.Preferred,
                QtWidgets.QSizePolicy.Ignored,
            )
        target = self._compute_geometry(expanded)

        def _apply() -> None:
            # 强制 layout 重新计算
            self.layout().invalidate()
            self.layout().activate()
            # 锁住目标尺寸,避免 layout sizeHint 把它拉回小尺寸
            self.setMinimumSize(target.width(), target.height())
            self.setMaximumSize(target.width(), target.height())
            self.setGeometry(target)
        QTimer.singleShot(0, _apply)
        if animated:
            QTimer.singleShot(30, lambda: self._animate_geometry(
                self._compute_geometry(expanded), self.ANIM_EXPAND_MS
            ))

    # ---------- 事件 ----------
    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key_Escape:
            self.hide()
            event.accept()
            return
        super().keyPressEvent(event)

    def changeEvent(self, event) -> None:  # noqa: N802
        if event.type() == QEvent.ActivationChange and not self.isActiveWindow():
            QTimer.singleShot(150, self._maybe_hide)
        super().changeEvent(event)

    def _maybe_hide(self) -> None:
        if not self.isVisible():
            return
        if self.isActiveWindow():
            return
        if self._anim and self._anim.state() == QAbstractAnimation.Running:
            return
        if self._child_dialog_open:
            return
        self.hide()

    # ---------- 流式气泡 ----------
    def _start_stream_bubble(self) -> None:
        """在历史区追加一个助手气泡（带 ▌ 占位），准备接 chunk"""
        ts = datetime.now().strftime("%H:%M")
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.End)
        # 强制在块边界插入,新气泡不会挤到上一行
        cursor.insertBlock()
        # header
        cursor.insertHtml(
            f'<p style="margin:0;padding:0;">'
            f'<span style="color:#7ee787;font-weight:600;">助手</span> '
            f'<span style="color:#5d626a;font-size:11px;">{ts}</span>'
            f'</p>'
        )
        # 留一个空 body block,记录它的起始位置
        body_start = self.history.textCursor().position()
        # 写入一个 zero-width 标记,后续会用它定位
        self.history.insertHtml(
            '<p style="color:#d6d6d6;margin:2px 0 8px 0;'
            'white-space:pre-wrap;line-height:1.65;"><span id="__stream_body__">'
            '<span style="color:#5d626a;">▌</span>'
            '</span></p>'
        )
        # 记录 body 段的"开始"(header 之后) 和"结束"(body 之后)
        self._stream_body_start = body_start
        self._stream_body_end = self.history.textCursor().position()
        self._stream_text = ""
        self._stream_active = True
        # 滚到底
        self._maybe_scroll_to_bottom(force=True)

    def _maybe_scroll_to_bottom(self, force: bool = False) -> None:
        """智能滚到底:如果用户已经在底部(或强制),就滚;否则不动,避免打断阅读。"""
        sb = self.history.verticalScrollBar()
        if force or sb.value() >= sb.maximum() - 8:
            sb.setValue(sb.maximum())

    def _update_stream_body(self) -> None:
        """用 _stream_text 的 MD 渲染结果替换 body 段。"""
        if self._stream_body_start is None or self._stream_body_end is None:
            return
        rendered = md.render(self._stream_text) or (
            '<span style="color:#5d626a;">▌</span>'
        )
        cursor = self.history.textCursor()
        cursor.setPosition(self._stream_body_start)
        cursor.setPosition(self._stream_body_end, QTextCursor.KeepAnchor)
        cursor.removeSelectedText()
        cursor.insertHtml(rendered)
        # 更新 body_end
        self._stream_body_end = self.history.textCursor().position()

    @pyqtSlot(str)
    def _on_chunk(self, chunk: str) -> None:
        if not self._stream_active:
            return
        self._stream_text += chunk
        self._update_stream_body()
        self._maybe_scroll_to_bottom()

    @pyqtSlot(str)
    def _on_reply(self, _full: str) -> None:
        # 流结束,最后再渲染一次(确保最终文本被 MD 处理)
        if self._stream_active:
            self._stream_active = False
            self._update_stream_body()
            self._stream_body_start = None
            self._stream_body_end = None
            self._stream_text = ""
        # memory 已在 agent.chat 里写过
        self._set_busy(False)
        self._set_status("idle", "就绪")

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        # 错误也走气泡
        if self._stream_active:
            self._stream_active = False
            self._stream_body_start = None
            self._stream_body_end = None
            self._stream_text = ""
        self._append_bubble("助手", msg)
        self._set_busy(False)
        self._set_status("error", "出错")

    # ---------- 发送 ----------
    def _on_send(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self._append_bubble("你", text)
        if not self._expanded:
            self._set_expanded(True, animated=True)

        if text.startswith("/"):
            self._handle_command(text)
            return

        self._start_stream_bubble()
        self._set_busy(True)
        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _worker(self, user_text: str) -> None:
        try:
            def on_chunk(c: str) -> None:
                self.sig_chunk.emit(c)
            reply = agent.chat(user_text, on_chunk=on_chunk)
            self.sig_reply.emit(reply)
        except Exception as e:
            self.sig_error.emit(f"出错：{e}")

    def _set_busy(self, busy: bool) -> None:
        self.btn_send.setEnabled(not busy)
        self.input.setReadOnly(busy)
        if busy:
            self._set_status("busy", "思考中…")
        # idle 在 _on_reply 里设,这样不会和 error 抢

    def _set_status(self, kind: str, tip: str = "") -> None:
        """状态点:idle(绿) / busy(黄,呼吸) / error(红)"""
        colors = {
            "idle": "#7ee787",
            "busy": "#e0c97a",
            "error": "#e58a8a",
        }
        color = colors.get(kind, "#7ee787")
        self.status_dot.setStyleSheet(
            f"color:{color};font-size:11px;background:transparent;border:none;"
        )
        if tip:
            self.status_dot.setToolTip(tip)
        # 呼吸动画(busy 时)
        if kind == "busy":
            if not hasattr(self, "_status_timer") or self._status_timer is None:
                self._status_timer = QTimer(self)
                self._status_timer.setInterval(700)
                self._status_timer.timeout.connect(self._pulse_status)
                self._status_alpha = 0
            self._status_timer.start()
        else:
            if hasattr(self, "_status_timer") and self._status_timer is not None:
                self._status_timer.stop()
            self.status_dot.setStyleSheet(
                f"color:{color};font-size:11px;background:transparent;border:none;"
            )

    def _pulse_status(self) -> None:
        if not hasattr(self, "_status_alpha"):
            self._status_alpha = 0
        self._status_alpha = (self._status_alpha + 1) % 2
        # 简单透明度变化
        opacity = 0.45 + 0.55 * (self._status_alpha)
        c = "#e0c97a"
        self.status_dot.setStyleSheet(
            f"color:{c};font-size:11px;background:transparent;border:none;"
            f"opacity:{opacity};"
        )

    # ---------- 气泡 ----------
    def _append_bubble(self, who: str, text: str) -> None:
        ts = datetime.now().strftime("%H:%M")
        if who == "你":
            role_color = "#8ab4ff"
            text_color = "#ececec"
        elif who == "助手":
            role_color = "#7ee787"
            text_color = "#d6d6d6"
        else:
            role_color = "#b0b0b0"
            text_color = "#b0b0b0"
        # 走 MD 渲染:用户消息一般不写 MD,但保险起见也渲染(标题/列表/代码 都生效)
        body_html = md.render(text)
        block = (
            f'<p style="margin:0;padding:0;">'
            f'<span style="color:{role_color};font-weight:600;">{who}</span> '
            f'<span style="color:#5d626a;font-size:11px;">{ts}</span>'
            f'</p>'
            f'<div style="color:{text_color};margin:2px 0 8px 0;'
            f'line-height:1.65;">{body_html}</div>'
        )
        if self.history.isHidden():
            self.history.show()
        cursor = self.history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertBlock()
        cursor.insertHtml(block)
        cursor.movePosition(QTextCursor.End)
        self.history.setTextCursor(cursor)
        self._maybe_scroll_to_bottom(force=True)

    # ---------- 指令 ----------
    def _handle_command(self, text: str) -> None:
        parts = text[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("help", "h", "?"):
            self._append_bubble("助手", _HELP_TEXT)
        elif cmd in ("clear", "new"):
            memory.reset_all()
            self.history.clear()
            self._set_expanded(False, animated=True)
            self._append_bubble("助手", "已清空对话")
        elif cmd == "settings":
            self._on_settings()
        elif cmd in ("prompt", "pref", "preferences", "提示词"):
            self._on_preferences()
        elif cmd == "model":
            if not arg:
                p = config.current_provider()
                self._append_bubble("助手",
                    f"当前：{p['name']} · {config.current_model()}")
            else:
                # /model 名称  → 切到当前提供方下的该模型（若不在列表里就当自定义）
                settings.set_value("model", arg)
                self._refresh_model_label()
                self._append_bubble("助手", f"已切换模型: {arg}")
        elif cmd in ("exit", "quit", "bye"):
            self._append_bubble("助手", "再见 👋（按 Esc 关闭，三连空格再次唤起）")
        else:
            self._append_bubble(
                "助手",
                f"未知指令 /{cmd}\n输入 /help 查看可用指令",
            )

    # ---------- 菜单 ----------
    def _on_attach(self) -> None:
        """+ 按钮 -> 更多菜单（设置/提示词/退出）"""
        menu = QtWidgets.QMenu(self)
        menu.addAction("设置…", self._on_settings)
        menu.addAction("更改提示词…", self._on_preferences)
        menu.addSeparator()
        menu.addAction("退出", QtWidgets.QApplication.instance().quit)
        menu.exec_(
            self.btn_attach.mapToGlobal(QtCore.QPoint(0, self.btn_attach.height()))
        )

    def _on_settings(self) -> None:
        self._child_dialog_open = True
        try:
            dlg = SettingsDialog(self)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                self.setStyleSheet(_build_style())
                self._refresh_model_label()
        finally:
            self._child_dialog_open = False
            if not self.isVisible():
                self.show_at_cursor()
            else:
                self.activateWindow()
                self.raise_()
                self.input.setFocus()

    def _on_preferences(self) -> None:
        self._child_dialog_open = True
        try:
            current = memory.get_preferences()
            text, ok = QtWidgets.QInputDialog.getMultiLineText(
                self, "更改提示词",
                "每行一条偏好，会拼到系统提示词末尾：\n"
                "（例如：回答简洁 / 用英文 / 代码示例要完整）",
                "\n".join(current),
            )
            if not ok:
                return
            memory.clear_preferences()
            for line in text.splitlines():
                line = line.strip()
                if line:
                    memory.add_preference(line)
            self._append_bubble(
                "系统",
                f"已保存 {len(memory.get_preferences())} 条提示词",
            )
        finally:
            self._child_dialog_open = False
            self.activateWindow()
            self.raise_()
            self.input.setFocus()

    def _on_clear(self) -> None:
        self._child_dialog_open = True
        try:
            ret = QtWidgets.QMessageBox.question(
                self, "确认", "清空所有对话历史和偏好？",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if ret == QtWidgets.QMessageBox.Yes:
                memory.reset_all()
                self.history.clear()
                self._set_expanded(False, animated=True)
        finally:
            self._child_dialog_open = False
            self.activateWindow()
            self.raise_()
            self.input.setFocus()


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )
