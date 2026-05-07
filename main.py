import os
import sys

# 强制将项目根目录加入到 Python 环境变量中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk
from gui.main_window import MainWindow

if __name__ == "__main__":
    ctk.set_appearance_mode("System") 
    ctk.set_default_color_theme("blue")
    
    app = MainWindow()
    
    # 🌟 新增：设置窗口左上角和底部任务栏的图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(icon_path):
        app.iconbitmap(icon_path)
        
    app.mainloop()