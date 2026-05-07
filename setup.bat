@echo off
echo 📡 正在为 NewsRadar 初始化环境...

:: 1. 创建虚拟环境 (建议起个通用的名字，比如 venv)
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请确保已安装 Python 并添加到环境变量。
    pause
    exit /b
)

:: 2. 激活环境并安装依赖
echo 📦 正在安装依赖库，请稍候...
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo ==========================================
    echo 🎉 环境配置全部完成！
    echo 💡 你现在可以双击运行 run.bat 来启动程序了！
    echo ==========================================
) else (
    echo ❌ 依赖安装失败，请检查网络连接或代理设置。
)

pause