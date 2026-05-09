@echo off
chcp 65001 >nul
title NewsRadar 自动打包工具 v2.0.0

echo ==========================================
echo 📦 正在编译 NewsRadar 2.0.0 (生产环境标准)
echo ==========================================
echo.

:: 1. 定义路径
set "VENV_PYTHON=%~dp0NewsRadar\Scripts\python.exe"
:: 🌟 明确定义：EXE 所在的根目录
set "EXE_ROOT=%~dp0dist\NewsRadar"

if not exist "%VENV_PYTHON%" (
    echo ❌ 错误：找不到虚拟环境！
    pause
    exit /b 1
)

echo [1/3] 正在清理旧的构建缓存...
if exist "build" rd /s /q "build"
if exist "dist\NewsRadar" rd /s /q "dist\NewsRadar"

echo [2/3] 正在执行 PyInstaller 核心编译...
:: 🌟 这里不使用任何 --add-data 包含 fonts，确保 PyInstaller 不会干扰它
"%VENV_PYTHON%" -m PyInstaller ^
    --noconsole ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --icon="icon.ico" ^
    --add-data "icon.ico;." ^
    --add-data "icon.svg;." ^
    --name "NewsRadar" ^
    --collect-all customtkinter ^
    --hidden-import dateutil ^
    --hidden-import markdown ^
    main.py

echo.
echo [3/3] 正在手动同步外部资源目录...
:: 🌟 强制在 .exe 的同级目录创建 fonts 文件夹
if not exist "%EXE_ROOT%\fonts" (
    echo 正在创建目录: "%EXE_ROOT%\fonts"
    mkdir "%EXE_ROOT%\fonts"
)

:: 🌟 物理拷贝占位文件
copy /Y "fonts\请自行放入字体文件.txt" "%EXE_ROOT%\fonts\" >nul

echo.
echo ==========================================
echo 🎉 编译成功！最终检查清单：
echo 1. 执行文件: "%EXE_ROOT%\NewsRadar.exe"
echo 2. 字体目录: "%EXE_ROOT%\fonts" (应包含说明文件)
echo ==========================================
pause