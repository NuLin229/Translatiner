@echo off
chcp 65001 >nul
title 音频翻译软件 - 启动器
color 0A

echo.
echo ╔════════════════════════════════════════════╗
echo ║       音频翻译软件 - 自动安装启动器        ║
echo ╚════════════════════════════════════════════╝
echo.

:: 检查 Python
echo [1/6] 检查 Python...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ╔════════════════════════════════════════════╗
    echo ║  错误: 未找到 Python                       ║
    echo ║                                            ║
    echo ║  请先安装 Python 3.9（推荐）              ║
    echo ║  下载地址: https://www.python.org         ║
    echo ║                                            ║
    echo ║  安装时务必勾选 "Add Python to PATH"      ║
    echo ╚════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)
echo     √ Python 已安装

:: 检查 FFmpeg
echo [2/6] 检查 FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ╔════════════════════════════════════════════╗
    echo ║  错误: 未找到 FFmpeg                       ║
    echo ║                                            ║
    echo ║  请安装 FFmpeg 并添加到系统 PATH          ║
    echo ║  下载: https://www.gyan.dev/ffmpeg/builds ║
    echo ║                                            ║
    echo ║  安装后需要重启电脑                       ║
    echo ╚════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)
echo     √ FFmpeg 已安装

:: 检查 Ollama
echo [3/6] 检查 Ollama...
ollama --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ╔════════════════════════════════════════════╗
    echo ║  错误: 未找到 Ollama                       ║
    echo ║                                            ║
    echo ║  请先安装 Ollama（本地AI翻译引擎）        ║
    echo ║  下载地址: https://ollama.com/download    ║
    echo ║                                            ║
    echo ║  安装后需要重启电脑                       ║
    echo ╚════════════════════════════════════════════╝
    echo.
    pause
    exit /b 1
)
echo     √ Ollama 已安装

:: 安装 Python 依赖
echo [4/6] 安装 Python 依赖（首次需要几分钟）...
pip install PyQt6 openai-whisper --quiet --disable-pip-version-check
if errorlevel 1 (
    echo     ! 部分依赖安装失败，尝试继续...
) else (
    echo     √ Python 依赖已安装
)

:: 下载 Ollama 模型
echo [5/6] 检查 AI 翻译模型（首次需要下载约2GB）...
ollama list | findstr "qwen2.5:3b" >nul 2>&1
if errorlevel 1 (
    echo     正在下载翻译模型，请耐心等待...
    ollama pull qwen2.5:3b
)
echo     √ AI 翻译模型已就绪

:: 启动 Ollama 服务
echo [6/6] 启动 Ollama 服务...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I /N "ollama.exe">NUL
if errorlevel 1 (
    start /B ollama serve >nul 2>&1
    timeout /t 3 /nobreak >nul
)
echo     √ Ollama 服务已启动

echo.
echo ╔════════════════════════════════════════════╗
echo ║       所有准备工作完成，正在启动...        ║
echo ╚════════════════════════════════════════════╝
echo.
echo 提示: 首次启动会下载语音识别模型（约1.5GB）
echo       请耐心等待，这只需要一次
echo.
timeout /t 2 /nobreak >nul

:: 启动主程序
cd /d "%~dp0"
python main.py

if errorlevel 1 (
    echo.
    echo 程序异常退出，请检查错误信息
    pause
)
