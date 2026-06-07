"""端到端冒烟：真起一次 QApplication + MainApp，跑 0.5s 退出。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _fix_pyqt5_plugins():
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return
    import importlib.util
    spec = importlib.util.find_spec("PyQt5")
    if spec and spec.origin:
        p = Path(spec.origin).parent / "Qt5" / "plugins" / "platforms"
        if p.exists():
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(p)


_fix_pyqt5_plugins()

from PyQt5 import QtWidgets
from PyQt5.QtCore import QTimer

import ui
import hotkey


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    win = ui.MainApp()

    triggered = []
    def cb():
        triggered.append(1)
        # 这里不真弹窗，只记一下回调
    listener = hotkey.TripleSpaceListener(callback=cb)
    listener.start()
    print(f"listener running: {listener._listener is not None and listener._listener.running}")

    QTimer.singleShot(500, app.quit)
    rc = app.exec_()
    listener.stop()
    print(f"event loop rc={rc}")
    print("GUI SMOKE OK")


if __name__ == "__main__":
    main()
