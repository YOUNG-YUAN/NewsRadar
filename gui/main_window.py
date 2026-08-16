import os
import time
import threading
import queue 
import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox as messagebox
from core.pipelines import FetcherThread, AnalyzerThread
from core.config_mgr import ConfigManager, VERSION 

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

class LongPressStopButton(ctk.CTkFrame):
    def __init__(self, master, width=120, height=45, command_click=None, command_stop=None, **kwargs):
        super().__init__(master, width=width, height=height, fg_color="transparent", **kwargs)
        self.pack_propagate(False) 
        
        self.command_click = command_click
        self.command_stop = command_stop
        
        self.is_paused = False
        self.width = width
        self.height = height
        
        self.press_time = 0
        self.timer_id = None
        self.is_pressing = False

        cr = 6

        self.base_btn = ctk.CTkButton(
            self, text="暂停获取", width=width, height=height,
            fg_color="#FFEB3B", hover_color="#FBC02D", text_color="black",
            corner_radius=cr, border_width=0, border_spacing=0,
            font=("Microsoft YaHei", 18, "bold")
        )
        self.base_btn.place(x=0, y=0)

        self.prog_frame = ctk.CTkFrame(
            self, width=0, height=height, corner_radius=0, 
            fg_color="#FFEB3B", bg_color="transparent"
        )
        self.prog_frame.place_forget()
        
        self.prog_btn = ctk.CTkButton(
            self.prog_frame, text="即将中止获取", width=width, height=height,
            fg_color="#F44336", hover_color="#F44336", text_color="white",
            corner_radius=cr, border_width=0, border_spacing=0,
            font=("Microsoft YaHei", 18, "bold")
        )
        self.prog_btn.place(x=0, y=0)

        for w in [self, self.base_btn, self.prog_frame, self.prog_btn]:
            w.bind("<ButtonPress-1>", self.on_press)
            w.bind("<ButtonRelease-1>", self.on_release)
            w.bind("<Leave>", self.on_leave)

    def abort_press(self):
        self.is_pressing = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if self.is_paused: self.set_paused()
        else: self.set_running()

    def set_running(self):
        self.is_paused = False
        self.base_btn.configure(text="暂停获取", fg_color="#FFEB3B", hover_color="#FBC02D", text_color="black")
        self.prog_frame.place_forget()

    def set_paused(self):
        self.is_paused = True
        self.base_btn.configure(text="恢复获取", fg_color="#8BC34A", hover_color="#7CB342", text_color="black")
        self.prog_frame.place_forget()

    def on_press(self, event):
        self.is_pressing = True
        self.press_time = time.time()
        if self.is_paused:
            self.check_long_press()

    def on_release(self, event):
        if not self.is_pressing: return
        self.is_pressing = False
        
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None

        duration = time.time() - self.press_time

        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()
        is_inside = (0 <= x <= self.width) and (0 <= y <= self.height)

        if not is_inside:
            if self.is_paused: self.set_paused()
            else: self.set_running()
            return

        if self.is_paused:
            if duration < 1.0: 
                if self.command_click: self.command_click()
            else: 
                self.set_paused()
        else:
            if self.command_click: self.command_click()

    def on_leave(self, event):
        if not self.is_pressing: return
        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()
        if x < -2 or x > self.width + 2 or y < -2 or y > self.height + 2:
            self.abort_press()

    def check_long_press(self):
        if not self.is_pressing: return
        elapsed = time.time() - self.press_time

        if elapsed >= 4.0:
            self.is_pressing = False
            self.prog_frame.place_forget()
            if self.command_stop: self.command_stop() 
            return
            
        elif elapsed >= 1.0:
            progress = (elapsed - 1.0) / 3.0
            new_width = min(int(self.width * progress), self.width)
            
            if self.base_btn.cget("text") != "即将中止获取":
                self.base_btn.configure(text="即将中止获取", fg_color="#FFEB3B", hover_color="#FFEB3B", text_color="black")
                self.prog_frame.configure(fg_color="#FFEB3B")

            self.prog_frame.configure(width=new_width)
            self.prog_frame.place(x=0, y=0)
            
        self.timer_id = self.after(20, self.check_long_press)


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
        self.status_queue = queue.Queue()  # 🌟 线程→主界面：停止状态标签更新

        self.init_ui()
        self.after(100, self.process_queues)

    def init_ui(self):
        self.frame_idle = ctk.CTkFrame(self, fg_color="transparent")
        
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
        
        # ==========================================
        # 🌟 运行状态顶栏改造
        # ==========================================
        self.frame_running = ctk.CTkFrame(self, fg_color="transparent")
        
        running_btn_frame = ctk.CTkFrame(self.frame_running, fg_color="transparent")
        running_btn_frame.pack(side="top", fill="x", pady=0)
        
        self.action_btn = LongPressStopButton(
            running_btn_frame, width=120, height=45,
            command_click=self.toggle_pause, command_stop=self.stop_pipelines
        )
        self.action_btn.pack(side="left", padx=(10, 5))

        # 🌟 新增：专门用于暂停时显示的蓝色按钮组
        self.running_settings_frame = ctk.CTkFrame(running_btn_frame, fg_color="transparent")
        
        btn_save_r = ctk.CTkButton(self.running_settings_frame, text="保存位置", fg_color="#008CBA", hover_color="#007399", 
                                 font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: SaveLocationDialog(self).wait_window())
        btn_ai_r = ctk.CTkButton(self.running_settings_frame, text="AI模型", fg_color="#008CBA", hover_color="#007399", 
                               font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: AIModelDialog(self).wait_window())
        btn_set_r = ctk.CTkButton(self.running_settings_frame, text="监听设置", fg_color="#008CBA", hover_color="#007399", 
                                font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: ListenSettingsDialog(self).wait_window())
        btn_pers_r = ctk.CTkButton(self.running_settings_frame, text="个性化", fg_color="#008CBA", hover_color="#007399", 
                                 font=("Microsoft YaHei", 14, "bold"), width=100, height=38, command=lambda: PersonalizationDialog(self).wait_window())
        
        btn_save_r.pack(side="left", padx=5)
        btn_ai_r.pack(side="left", padx=5)
        btn_set_r.pack(side="left", padx=5)
        btn_pers_r.pack(side="left", padx=5)
        # 注意：此处不调用 .pack()，确保初始处于隐藏状态

        lbl_v_run = ctk.CTkLabel(running_btn_frame, text=VERSION, font=("Microsoft YaHei", 14, "bold"), text_color="#A0A0A0")
        lbl_v_run.pack(side="right", padx=15)

        running_info_frame = ctk.CTkFrame(self.frame_running, fg_color="transparent")
        running_info_frame.pack(side="top", fill="x", padx=10, pady=(2, 0))
        
        self.lbl_ai_info = ClickableTruncatedLabel(running_info_frame, text="", max_length=45, font=("Microsoft YaHei", 14), text_color="#A0A0A0")
        self.lbl_save_info = ClickableTruncatedLabel(running_info_frame, text="", max_length=50, font=("Microsoft YaHei", 14), text_color="#A0A0A0")
        
        self.lbl_ai_info.pack(side="left", pady=0)
        self.lbl_save_info.pack(side="right", pady=0)

        # ==========================================
        log_container = ctk.CTkFrame(self, fg_color="transparent")
        log_container.pack(fill="both", expand=True, padx=20, pady=(5, 10))
        
        self.log_area = ctk.CTkTextbox(log_container, font=("Consolas", 13), border_color="#555555", border_width=2)
        self.log_area.tag_config("RED_ALERT", foreground="#F44336")
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
            
            if "[RED_ALERT]" in text:
                clean_text = text.replace("[RED_ALERT]", "").strip()
                self.log_area.insert("end", f"[{timestamp}] {clean_text}\n", "RED_ALERT")
            else:
                self.log_area.insert("end", f"[{timestamp}] {text}\n")
                
            self.log_area.see("end")

        while not self.token_queue.empty():
            val = self.token_queue.get()
            self.lbl_tokens.configure(text=f"已消耗 {val} tokens")

        while not self.status_queue.empty():
            val = self.status_queue.get()
            self.lbl_time.configure(text=val)

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
        # 🌟 防双开：上一次任务的后台线程若仍在收尾，拒绝再次启动（避免双重抓取/烧 token）
        if (self.fetcher and self.fetcher.is_alive()) or (self.analyzer and self.analyzer.is_alive()):
            messagebox.showwarning("任务仍在运行", "上一次任务的后台线程仍在收尾，请等待其完全结束（观察日志提示）后再开始。")
            return

        self.config = ConfigManager.load_config()
        self.frame_idle.pack_forget()
        self.frame_running.pack(fill="x", padx=10, pady=(15, 0), before=self.log_area.master)
        
        self.is_paused = False
        self.action_btn.set_running()
        self.running_settings_frame.pack_forget() # 🌟 启动时确保设置按钮隐藏
        
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
        self.analyzer = AnalyzerThread(
            log_callback=self.write_log, 
            token_callback=self.update_tokens,
            fetcher_ref=self.fetcher 
        )
        
        self.fetcher.start()
        self.analyzer.start()

    def toggle_pause(self):
        if not self.is_running: return
        
        if self.is_paused:
            # 🌟 正在恢复执行
            self.is_paused = False
            self.action_btn.set_running()
            if self.fetcher: self.fetcher.is_paused = False
            if self.analyzer: self.analyzer.is_paused = False
            
            self.running_settings_frame.pack_forget() # 🌟 恢复获取时隐藏设置按钮
            
            self.start_time += (time.time() - getattr(self, 'pause_start_time', time.time()))
            self.write_log("▶️ 任务已恢复")
            self.status_indicator.set_color("#4CAF50")
        else:
            # 🌟 正在进入暂停
            self.is_paused = True
            self.action_btn.set_paused()
            if self.fetcher: self.fetcher.is_paused = True
            if self.analyzer: self.analyzer.is_paused = True
            
            self.running_settings_frame.pack(side="left", padx=5) # 🌟 暂停时滑出设置按钮
            
            self.pause_start_time = time.time()
            self.write_log("⏸️ 任务已暂停 (后台线程挂起中...)")
            self.status_indicator.set_color("#FFEB3B")

    def stop_pipelines(self):
        self.write_log("正在中止任务，等待当前操作结束...")
        self.is_running = False
        
        if self.fetcher: self.fetcher.stop()
        if self.analyzer: self.analyzer.stop()
        
        self.status_indicator.set_color("#F44336")
        self.lbl_time.configure(text="正在中止…")  # 🌟 如实显示：线程可能仍在收尾

        self.frame_running.pack_forget()
        self.frame_idle.pack(fill="x", padx=10, pady=15, before=self.log_area.master)

        threading.Thread(target=self._monitor_shutdown, daemon=True).start()

    def _monitor_shutdown(self):
        # 🌟 等待窗口覆盖最坏在途请求（LLM 120s + 抓取 15s×3 重试），不再 15s 谎报"已中止"
        for _ in range(150):
            is_alive = False
            if self.fetcher and self.fetcher.is_alive(): is_alive = True
            if self.analyzer and self.analyzer.is_alive(): is_alive = True
            if not is_alive:
                self.status_queue.put("程序已停止")
                self.write_log("✅ 任务已中止")
                return
            time.sleep(1)

        self.write_log("⚠️ 后台线程仍在收尾（LLM 请求可能未结束）。已请求停止；请稍候或关闭窗口，勿立即重新启动。")

    def update_timer(self):
        if self.is_running:
            if not getattr(self, 'is_paused', False):
                elapsed = int(time.time() - self.start_time)
                h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
                self.lbl_time.configure(text=f"程序已运行 {h:02d}h {m:02d}m {s:02d}s")
            self.after(1000, self.update_timer)