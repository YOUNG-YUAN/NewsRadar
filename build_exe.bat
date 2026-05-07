@echo off
chcp 65001 >nul
title NewsRadar 自动打包工具

echo ==========================================
echo 📦 正在准备将 NewsRadar 编译为 EXE 桌面软件...
echo ==========================================
echo.

:: 🌟 绝杀：动态获取当前文件夹的绝对路径，并拼接出虚拟环境里 python.exe 的绝对路径
set "VENV_PYTHON=%~dp0NewsRadar\Scripts\python.exe"

echo [1/3] 验证虚拟环境 Python 引擎...
echo 当前使用的 Python 引擎为: %VENV_PYTHON%
if not exist "%VENV_PYTHON%" (
    echo.
    echo ❌ 错误：找不到虚拟环境！请确保你已经运行过 setup.bat 并且生成了 NewsRadar 文件夹！
    pause
    exit /b 1
)

echo.
echo [2/3] 正在虚拟环境中安装打包引擎 (PyInstaller)...
:: 🌟 绝对锁定使用虚拟环境的 Python去安装
"%VENV_PYTHON%" -m pip install pyinstaller

echo.
echo [3/3] 正在执行核心编译... (这可能需要 2-3 分钟，请勿关闭窗口)
:: 🌟 绝对锁定使用虚拟环境的 Python去执行打包！
:: 🌟 增加了 --add-data "icon.ico;." 确保图标文件被复制进打包目录
"%VENV_PYTHON%" -m PyInstaller --noconsole --noconfirm --onedir --windowed --icon="icon.ico" --add-data "icon.ico;." --name "NewsRadar" --collect-all customtkinter --hidden-import dateutil main.py
echo.
echo ==========================================
echo 🎉 Success! The EXE has been generated in the [dist] folder!
echo ==========================================
pause