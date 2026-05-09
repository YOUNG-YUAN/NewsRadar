import os
import time
import threading
import queue 
import customtkinter as ctk
import tkinter.messagebox as messagebox
from core.pipelines import FetcherThread, AnalyzerThread
from core.config_mgr import ConfigManager, VERSION 

# 🌟 修复：完整引入所有拆分后的弹窗组件（包括 PersonalizationDialog）
from .dialog_sys import SaveLocationDialog, PersonalizationDialog
from .dialog_ai import AIModelDialog
from .dialog_rss import ListenSettingsDialog

class ClickableTruncatedLabel(ctk.CTkLabel):
    def __init__(self, master, text="", max_length=50, **kwargs):
        super().__init__(master, text=self._truncate(text, max_length), **kwargs)
        self.full_text = text
        self.max_length = max_length
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def _truncate(self, text, length):
        if len(text) <= length:
            return text
        return text[:length] + "..."

    def set_text(self, text):
        self.full_text = text
        self.configure(text=self._truncate(text, self.max_length))

    def on_enter(self, event):
        self.configure(text=self.full_text)

    def on_leave(self, event):
        self.configure(text=self._truncate(self.full_text, self.max_length))

    def on_click(self, event):
        self.clipboard_clear()
        self.clipboard_append(self.full_text)
        messagebox.showinfo("提示", "已复制内容到剪贴板！")

class StatusIndicator(ctk.CTkFrame):
    def __init__(self, master, color="#FFEB3B", size=20, **kwargs):
        super().__init__(master, width=size, height=size, corner_radius=size//2, fg_color=color, **kwargs)
    
    def set_color(self, color):
        self.configure(fg_color=color)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"AI 新闻雷达 {VERSION}")
        self.geometry("900x600")
        self.resizable(False, False)
        
        self.config = ConfigManager.load_config()
        self.is_running = False
        self.is_paused = False
        self.start_time = 0
        
        self.fetcher = None
        self.analyzer = None

        self.log_queue = queue.Queue()
        self.token_queue = queue.Queue()

        self.init_ui()
        self.after(100, self.process_queues)

    def init_ui(self):
        self.frame_idle = ctk.CTkFrame(self, fg_color="transparent")
        
        # 🌟 调整按钮的宽度分布，确保 5 个按钮整齐排列
        btn_start = ctk.CTkButton(self.frame_idle, text="开始获取", fg_color="#4CAF50", hover_color="#45a049", 
                                  font=("Microsoft YaHei", 18, "bold"), width=120, height=45, command=self.start_pipelines)
        
        btn_save = ctk.CTkButton(self.frame_idle, text="保存位置", fg_color="#008CBA", hover_color="#007399", 
                                 font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: SaveLocationDialog(self).wait_window())
        btn_ai = ctk.CTkButton(self.frame_idle, text="AI模型", fg_color="#008CBA", hover_color="#007399", 
                               font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: AIModelDialog(self).wait_window())
        btn_set = ctk.CTkButton(self.frame_idle, text="监听设置", fg_color="#008CBA", hover_color="#007399", 
                                font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: ListenSettingsDialog(self).wait_window())
        
        btn_pers = ctk.CTkButton(self.frame_idle, text="个性化", fg_color="#008CBA", hover_color="#007399", 
                                 font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: PersonalizationDialog(self).wait_window())
        
        btn_start.pack(side="left", padx=(10, 5))
        btn_save.pack(side="left", padx=5)
        btn_ai.pack(side="left", padx=5)
        btn_set.pack(side="left", padx=5)
        btn_pers.pack(side="left", padx=5)
        
        lbl_v_idle = ctk.CTkLabel(self.frame_idle, text=VERSION, font=("Microsoft YaHei", 14, "bold"), text_color="#A0A0A0")
        lbl_v_idle.pack(side="right", padx=15)
        
        self.frame_idle.pack(fill="x", padx=10, pady=15)
        
        self.frame_running = ctk.CTkFrame(self, fg_color="transparent")
        
        self.btn_pause = ctk.CTkButton(self.frame_running, text="暂停获取", fg_color="#FFEB3B", text_color="black", 
                                  hover_color="#FBC02D", font=("Microsoft YaHei", 18, "bold"), width=140, height=45, command=self.toggle_pause)
        
        btn_stop = ctk.CTkButton(self.frame_running, text="中止获取", fg_color="#F44336", hover_color="#D32F2F", 
                                 font=("Microsoft YaHei", 18, "bold"), width=140, height=45, command=self.stop_pipelines)
        
        self.btn_pause.pack(side="left", padx=10)
        btn_stop.pack(side="left", padx=10)

        lbl_v_run = ctk.CTkLabel(self.frame_running, text=VERSION, font=("Microsoft YaHei", 14, "bold"), text_color="#A0A0A0")
        lbl_v_run.pack(side="right", padx=20)

        info_frame = ctk.CTkFrame(self.frame_running, fg_color="transparent")
        info_frame.pack(side="left", padx=20, fill="both", expand=True)
        
        self.lbl_ai_info = ClickableTruncatedLabel(info_frame, text="", max_length=45, font=("Microsoft YaHei", 14), text_color="#A0A0A0")
        self.lbl_save_info = ClickableTruncatedLabel(info_frame, text="", max_length=45, font=("Microsoft YaHei", 14), text_color="#A0A0A0")
        self.lbl_ai_info.pack(anchor="w", pady=2)
        self.lbl_save_info.pack(anchor="w", pady=2)

        log_container = ctk.CTkFrame(self, fg_color="transparent")
        log_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.log_area = ctk.CTkTextbox(log_container, font=("Consolas", 13), border_color="#555555", border_width=2)
        self.log_area.pack(fill="both", expand=True)
        
        self.watermark = ctk.CTkLabel(log_container, text="运行日志", font=("Microsoft YaHei", 24, "bold"), text_color="#555555")
        self.watermark.place(relx=0.5, rely=0.5, anchor="center")

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_indicator = StatusIndicator(bottom_frame, color="#FFEB3B", size=18)
        self.status_indicator.pack(side="left", padx=(5, 10))
        
        self.lbl_time = ctk.CTkLabel(bottom_frame, text="程序未启动", font=("Microsoft YaHei", 14))
        self.lbl_tokens = ctk.CTkLabel(bottom_frame, text=f"已消耗 {self.config.get('total_tokens', 0)} tokens", font=("Microsoft YaHei", 14))
        self.lbl_freq = ctk.CTkLabel(bottom_frame, text="监听频率 未设定", font=("Microsoft YaHei", 14))

        self.lbl_time.pack(side="left")
        self.lbl_freq.pack(side="right", padx=10)
        self.lbl_tokens.pack(side="right", padx=20)

    def write_log(self, text):
        self.log_queue.put(text)

    def update_tokens(self, val):
        self.token_queue.put(val)

    def process_queues(self):
        while not self.log_queue.empty():
            text = self.log_queue.get()
            if self.watermark.winfo_ismapped():
                self.watermark.place_forget()
            timestamp = time.strftime('%H:%M:%S')
            self.log_area.insert("end", f"[{timestamp}] {text}\n")
            self.log_area.see("end")

        while not self.token_queue.empty():
            val = self.token_queue.get()
            self.lbl_tokens.configure(text=f"已消耗 {val} tokens")

        self.after(100, self.process_queues)

    def format_human_readable_freq(self, freq_str):
        try:
            val, unit = int(freq_str[:-1]), freq_str[-1].lower()
            if unit == 'm': total_mins = val
            elif unit == 'h': total_mins = val * 60
            elif unit == 'd': total_mins = val * 24 * 60
            else: return freq_str
        except: return freq_str

        d = total_mins // (24 * 60)
        h = (total_mins % (24 * 60)) // 60
        m = total_mins % 60

        result = []
        if d > 0: result.append(f"{d} d")
        if h > 0 or d > 0: result.append(f"{h} h")
        result.append(f"{m} min") 
        return " ".join(result)

    def start_pipelines(self):
        self.config = ConfigManager.load_config()
        self.frame_idle.pack_forget()
        self.frame_running.pack(fill="x", padx=20, pady=15, before=self.log_area.master)
        
        self.is_paused = False
        self.btn_pause.configure(text="暂停获取", fg_color="#FFEB3B", hover_color="#FBC02D")
        
        provider = self.config.get('ai_provider', 'Google Gemini')
        model_name = self.config.get('providers', {}).get(provider, {}).get('model', 'Unknown')
        
        self.lbl_ai_info.set_text(f"已调用 {provider} ({model_name}) 大模型")
        
        save_abs_path = os.path.abspath(self.config['save_path'])
        self.lbl_save_info.set_text(f"报告将保存至 {save_abs_path}")

        self.status_indicator.set_color("#4CAF50")
        
        raw_freq = self.config.get('listen_freq', '60m')
        self.lbl_freq.configure(text=f"监听频率 {self.format_human_readable_freq(raw_freq)}")
        
        self.start_time = time.time()
        self.is_running = True
        self.update_timer()

        self.log_area.delete("1.0", "end") 
        self.write_log("系统启动中...")

        self.fetcher = FetcherThread(log_callback=self.write_log)
        self.analyzer = AnalyzerThread(log_callback=self.write_log, token_callback=self.update_tokens)
        
        self.fetcher.start()
        self.analyzer.start()

    def toggle_pause(self):
        if not self.is_running: return
        
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.configure(text="暂停获取", fg_color="#FFEB3B", hover_color="#FBC02D")
            if self.fetcher: self.fetcher.is_paused = False
            if self.analyzer: self.analyzer.is_paused = False
            
            self.start_time += (time.time() - getattr(self, 'pause_start_time', time.time()))
            self.write_log("▶️ 任务已恢复")
            self.status_indicator.set_color("#4CAF50")
        else:
            self.is_paused = True
            self.btn_pause.configure(text="恢复获取", fg_color="#8BC34A", hover_color="#7CB342")
            if self.fetcher: self.fetcher.is_paused = True
            if self.analyzer: self.analyzer.is_paused = True
            
            self.pause_start_time = time.time()
            self.write_log("⏸️ 任务已暂停 (后台线程挂起中...)")
            self.status_indicator.set_color("#FFEB3B")

    def stop_pipelines(self):
        self.write_log("正在中止任务，等待当前操作结束...")
        self.is_running = False
        
        if self.fetcher: self.fetcher.stop()
        if self.analyzer: self.analyzer.stop()
        
        self.status_indicator.set_color("#F44336")
        self.lbl_time.configure(text="程序已停止")
        
        self.frame_running.pack_forget()
        self.frame_idle.pack(fill="x", padx=20, pady=15, before=self.log_area.master)
        
        threading.Thread(target=self._monitor_shutdown, daemon=True).start()

    def _monitor_shutdown(self):
        for _ in range(15):
            is_alive = False
            if self.fetcher and self.fetcher.is_alive(): is_alive = True
            if self.analyzer and self.analyzer.is_alive(): is_alive = True
            if not is_alive: break
            time.sleep(1)
            
        self.write_log("✅ 任务已中止")

    def update_timer(self):
        if self.is_running:
            if not getattr(self, 'is_paused', False):
                elapsed = int(time.time() - self.start_time)
                h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                self.lbl_time.configure(text=f"程序已运行 {h:02d}h {m:02d}m {s:02d}s")
            self.after(1000, self.update_timer)