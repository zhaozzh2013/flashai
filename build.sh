#!/usr/bin/env bash
# Build 智能助手 / FlashAI for macOS or Linux.
# 用法:   ./build.sh            # 一次性构建当前平台
#        ./build.sh --clean    # 先清理 build/ dist/ 再构建
#
# 产出:
#   macOS  → dist/FlashAI/FlashAI.app   (通过 `--osx-bundle-identifier` 可选)
#   Linux  → dist/flashai/flashai
#
# 注意:本脚本只在 macOS / Linux 上有意义。Windows 请用 `pyinstaller flashai.spec`。
set -euo pipefail

cd "$(dirname "$0")"

PLATFORM="$(uname -s)"
echo "==> 平台: $PLATFORM"

if [[ "$PLATFORM" != "Darwin" && "$PLATFORM" != "Linux" ]]; then
    echo "错误:此脚本只支持 macOS / Linux。Windows 用户请直接运行 pyinstaller flashai.spec" >&2
    exit 1
fi

# 可选:清理
if [[ "${1:-}" == "--clean" ]]; then
    echo "==> 清理 build/ dist/"
    rm -rf build dist *.egg-info
fi

# 优先使用本地 .venv,没有就用系统 python
if [[ -x ".venv/bin/python" ]]; then
    PY=".venv/bin/python"
    echo "==> 使用本地 venv: $PY"
else
    PY="$(command -v python3)"
    echo "==> 使用系统 Python: $PY"
fi

# 安装依赖
echo "==> 安装依赖"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r requirements.txt pyinstaller >/dev/null

# 构建
echo "==> 运行 pyinstaller"
"$PY" -m PyInstaller flashai.spec --noconfirm

case "$PLATFORM" in
    Darwin)
        echo "==> 完成:dist/FlashAI/FlashAI"
        echo "    双击 FlashAI 启动;或用命令行 open dist/FlashAI/FlashAI"
        ;;
    Linux)
        echo "==> 完成:dist/flashai/flashai"
        echo "    直接运行 ./dist/flashai/flashai"
        # AppImage / deb 可后续加 linuxdeploy
        ;;
esac
