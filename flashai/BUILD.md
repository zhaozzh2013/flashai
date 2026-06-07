# 构建说明 / Build Instructions

## 在 GitHub 上自动构建(推荐)

推送一个 `v*` 标签即可触发 `.github/workflows/release.yml`,自动构建 Windows / macOS / Linux 三个平台并发布到 GitHub Release:

```bash
git tag v0.01
git push origin v0.01
```

构建产物命名:
- `FlashAI-Windows-x64.zip`  →  解压后双击 `智能助手.exe`
- `FlashAI-macOS-arm64.zip`  →  双击 `FlashAI`(首次需右键 → 打开绕过 Gatekeeper)
- `FlashAI-Linux-x64.zip`    →  `./flashai`

## 本地构建

### Windows

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt pyinstaller
pyinstaller flashai.spec --noconfirm --clean
# 产出:dist\智能助手\智能助手.exe
```

> **路径提示**:如果你的项目路径含中文,PyInstaller 的 PyQt5 hook 可能会失败。建议把仓库放在全 ASCII 路径,或直接在 GitHub 上跑 Actions。

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt pyinstaller
./build.sh            # 或 ./build.sh --clean
# macOS  →  dist/FlashAI/FlashAI
# Linux  →  dist/flashai/flashai
```

## 调试构建问题

- 加 `--log-level DEBUG` 看 PyInstaller 详细日志
- 加 `console=True` 临时打开黑色控制台看错误
- 排除模块不够:在 `flashai.spec` 的 `excludes` 列表里增删
- 体积过大:加 `--exclude-module` / 删 `upx=True` / 用 UPX 预压缩
