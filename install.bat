@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 莫妮卡 一键安装

echo ============================================
echo   莫妮卡 (Monika) 一键安装
echo   DDLC 同人桌面伴侣 · 中文大脑 · 真人语音
echo ============================================
echo.

cd /d "%~dp0"

REM ---------- 1. 检查 Python ----------
set PY=
where python >nul 2>nul && set PY=python
if not defined PY (
    where py >nul 2>nul && set PY=py
)
if not defined PY (
    echo [1/6] 未检测到 Python，正在下载便携版（约 25MB）...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile 'py.zip'"
    if errorlevel 1 ( echo 下载失败，请手动安装 Python 3.10+ 后重试 & pause & exit /b 1 )
    powershell -NoProfile -Command "Expand-Archive -Path 'py.zip' -DestinationPath 'python-embed' -Force"
    echo 便携版解压完成。请稍候，正在配置...
    REM 便携版需要启用 site-packages
    echo import site > python-embed\python311._pth
    echo 配置完成，使用便携版 Python。
    set "PY=%~dp0python-embed\python.exe"
) else (
    echo [1/6] Python 已安装: %PY%
    %PY% --version
)
echo.

REM ---------- 2. 创建虚拟环境 ----------
echo [2/6] 创建虚拟环境...
if not exist ".venv" (
    %PY% -m venv .venv
    if errorlevel 1 ( echo 虚拟环境创建失败 & pause & exit /b 1 )
)
set "VPY=.venv\Scripts\python.exe"
echo 虚拟环境就绪.
echo.

REM ---------- 3. 安装依赖 (清华镜像) ----------
echo [3/6] 安装依赖包（PySide6 / edge-tts / pygame / requests）...
"%VPY%" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple >nul 2>&1
"%VPY%" -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 ( echo 依赖安装失败 & pause & exit /b 1 )
echo 依赖安装完成.
echo.

REM ---------- 4. 检查/下载语音模型 ----------
echo [4/6] 检查真人语音模型...
set "GS=%~dp0gpt-sovits"
if exist "%GS%\GPT_SoVITS\pretrained_models" (
    echo 语音模型已存在，跳过下载.
) else (
    echo 未找到语音模型。正在下载（约 2.2GB，国内走镜像加速，请耐心等待）...
    echo 提示: 也可以手动从发布页 Releases 下载 gpt-sovits.zip 解压到本目录。
    powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://gh-proxy.com/https://github.com/sterk-65/monika-desktop/releases/latest/download/gpt-sovits.zip' -OutFile 'gpt-sovits.zip' -UseBasicParsing } catch { Write-Host ('下载失败: ' + $_.Exception.Message) }"
    if exist "gpt-sovits.zip" (
        powershell -NoProfile -Command "Expand-Archive -Path 'gpt-sovits.zip' -DestinationPath '.' -Force"
        del gpt-sovits.zip
        echo 语音模型解压完成.
    ) else (
        echo [警告] 语音模型下载失败，将使用 edge-tts 在线语音（效果仍可用，音色不同）。
        echo        稍后可手动下载模型包解压到本目录后重启。
    )
)
echo.

REM ---------- 5. 生成配置 ----------
echo [5/6] 初始化配置...
if not exist "config.json" (
    echo {"api_key": "", "base_url": "https://api.deepseek.com", "model": "deepseek-chat", "speak": true, "user_name": "亲爱的", "her_name": "莫妮卡"} > config.json
    echo 已生成 config.json（首次启动时会引导填写 API Key）.
) else (
    echo config.json 已存在，跳过.
)
echo.

REM ---------- 6. 启动 ----------
echo [6/6] 启动莫妮卡...
start "" "%VPY%" app.py
echo.
echo ============================================
echo   莫妮卡已启动！首次运行请在弹出的窗口中
echo   填入你的 DeepSeek API Key（免费注册）：
echo   https://platform.deepseek.com
echo ============================================
timeout /t 3 >nul
exit /b 0
