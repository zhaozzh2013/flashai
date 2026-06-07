"""冒烟测试：不启动 GUI，只验证模块能 import + 关键功能。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def test_imports():
    import config
    print(f"[config] data_dir={config.DATA_DIR} "
          f"provider={config.current_provider_key()} "
          f"model={config.current_model()} "
          f"has_key={bool(config.current_api_key())}")
    import memory
    print("[memory] OK")
    import web_search
    print("[web_search] OK")
    import agent
    print(f"[agent] needs_search('今天天气')={agent.needs_search('今天天气')} "
          f"needs_search('1+1')={agent.needs_search('1+1')}")
    import hotkey
    print("[hotkey] OK")
    import autostart
    print(f"[autostart] is_enabled={autostart.is_enabled()}")


def test_memory():
    import memory
    # 不污染现有数据：用临时文件
    import config, json, tempfile
    tmp = Path(tempfile.mkdtemp()) / "memory.json"
    orig = config.MEMORY_FILE
    config.MEMORY_FILE = tmp
    try:
        memory.add_message("user", "hello")
        memory.add_message("assistant", "hi")
        memory.add_preference("回答简洁")
        msgs = memory.get_recent_messages()
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert memory.get_preferences() == ["回答简洁"]
        print("[memory] roundtrip OK")
    finally:
        config.MEMORY_FILE = orig


def test_search_format():
    import web_search
    out = web_search.format_for_prompt("q", [])
    assert out == ""
    out2 = web_search.format_for_prompt("q", [{"error": "fail"}])
    assert "联网搜索失败" in out2
    print("[web_search] format OK")


def test_hotkey_logic():
    """不真起 pynput 监听器，单元测试时间窗口逻辑"""
    import hotkey, time
    cb_calls = []
    cb = lambda: cb_calls.append(1)
    listener = hotkey.TripleSpaceListener(callback=cb, presses=3,
                                          window_ms=1200, gap_ms=450)
    # 模拟三次按 space（在窗口内）
    for _ in range(3):
        listener._on_press(hotkey.keyboard.Key.space)
        time.sleep(0.05)
    assert len(cb_calls) == 1, f"expected 1 trigger, got {len(cb_calls)}"
    print("[hotkey] 3-press trigger OK")

    # 模拟"过慢"，不应触发
    cb_calls.clear()
    listener2 = hotkey.TripleSpaceListener(callback=cb, presses=3,
                                           window_ms=200, gap_ms=100)
    listener2._on_press(hotkey.keyboard.Key.space)
    time.sleep(0.3)  # 超窗口
    listener2._on_press(hotkey.keyboard.Key.space)
    listener2._on_press(hotkey.keyboard.Key.space)
    assert len(cb_calls) == 0, f"expected 0 trigger, got {len(cb_calls)}"
    print("[hotkey] expired window ignored OK")


if __name__ == "__main__":
    test_imports()
    test_memory()
    test_search_format()
    test_hotkey_logic()
    print("\nALL SMOKE TESTS PASSED")
