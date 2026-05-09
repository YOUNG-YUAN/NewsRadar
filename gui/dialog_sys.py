import os
import tkinter as tk
import customtkinter as ctk
from core.config_mgr import ConfigManager, FONTS_DIR

class SaveLocationDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("保存位置")
        self.geometry("800x450")
        self.grab_set() 
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        ctk.CTkLabel(self, text="保存位置", font=("Microsoft YaHei", 24, "bold")).pack(pady=20)
        
        switch_frame = ctk.CTkFrame(self, fg_color="transparent")
        switch_frame.pack(fill="x", padx=40, pady=(0, 10))
        
        self.switch_md = ctk.CTkSwitch(switch_frame, text="输出 Markdown 文件", font=("Microsoft YaHei", 14, "bold"))
        self.switch_md.pack(side="left", padx=(0, 30))
        if self.config.get('export_md', True): self.switch_md.select()
        
        self.switch_pdf = ctk.CTkSwitch(switch_frame, text="输出 PDF 文件", font=("Microsoft YaHei", 14, "bold"))
        self.switch_pdf.pack(side="left")
        if self.config.get('export_pdf', True): self.switch_pdf.select()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=10)
        ctk.CTkButton(btn_frame, text="保存至文件夹", font=("Microsoft YaHei", 14), fg_color="#008CBA", hover_color="#006b8f", command=self.select_folder).pack(side="left")

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(fill="x", padx=40, pady=20)
        ctk.CTkLabel(form_frame, text="保存路径", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.path_entry = ctk.CTkEntry(form_frame, width=500, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.path_entry.grid(row=0, column=1, pady=10, sticky="w")
        self.path_entry.insert(0, self.config['save_path'])

        ctk.CTkLabel(form_frame, text="文件名", font=("Microsoft YaHei", 14)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(form_frame, width=500, font=("Microsoft YaHei", 14), border_color="#A0A0A0", border_width=1, fg_color="#E0E0E0", text_color="#555555")
        self.name_entry.grid(row=1, column=1, pady=10, sticky="w")
        self.name_entry.insert(0, "NewsSummary_YYYY-MM-DD-HHMM.<格式>")
        self.name_entry.configure(state="readonly")
        ctk.CTkLabel(self, text="注：YYYY-MM-DD-HHMM对应于发起监听的年-月-日-时-分", font=("Microsoft YaHei", 12)).pack(pady=10)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=40, pady=20)
        ctk.CTkButton(bottom_frame, text="保存", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", hover_color="#006b8f", command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", hover_color="#909090", command=self.destroy).pack(side="right")

    def select_folder(self):
        folder = ctk.filedialog.askdirectory(initialdir=self.path_entry.get())
        if folder:
            self.path_entry.delete(0, 'end'); self.path_entry.insert(0, folder)

    def save_data(self):
        self.config['save_path'] = self.path_entry.get()
        self.config['export_md'] = bool(self.switch_md.get())
        self.config['export_pdf'] = bool(self.switch_pdf.get())
        ConfigManager.save_config(self.config)
        self.destroy()

class PersonalizationDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("排版字体设置")
        self.geometry("1100x700")
        self.grab_set() 
        self.config = ConfigManager.load_config()
        self.font_list = ["(系统默认)"] + self._get_local_fonts()
        self.font_vars = {}
        self.zoom_factor = 1.0 
        self.init_ui()
        self.update_preview()

    def _get_local_fonts(self):
        if not os.path.exists(FONTS_DIR): return []
        return [f for f in os.listdir(FONTS_DIR) if f.lower().endswith(('.ttf', '.ttc', '.otf'))]

    def _analyze_font_file(self, filename):
        if not filename or filename == "(系统默认)":
            return "Microsoft YaHei", "normal", "roman"
        fn = filename.lower()
        family, weight, slant = "Microsoft YaHei", "normal", "roman"
        if "msyh" in fn or "yahei" in fn: family = "Microsoft YaHei"
        elif "simsun" in fn or "song" in fn: family = "SimSun"
        elif "stzhong" in fn: family = "STZhongsong"
        elif "harmony" in fn: family = "Microsoft YaHei"
        elif "consol" in fn: family = "Consolas"
        elif "times" in fn: family = "Times New Roman"
        elif "arial" in fn: family = "Arial"

        basename = os.path.splitext(fn)[0]
        if "bolditalic" in fn or basename.endswith("bi"): weight, slant = "bold", "italic"
        elif "bold" in fn or basename.endswith("bd"): weight = "bold"
        elif "italic" in fn or basename.endswith("i"): slant = "italic"
        return family, weight, slant

    def on_zoom_change(self, val):
        self.zoom_factor = float(val)
        self.lbl_zoom_val.configure(text=f"{self.zoom_factor:.1f}x")
        self.update_preview()

    def init_ui(self):
        ctk.CTkLabel(self, text="排版字体个性化", font=("Microsoft YaHei", 24, "bold")).pack(pady=(15, 5))
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=5)
        left_frame = ctk.CTkFrame(main_frame, fg_color="transparent", width=400)
        left_frame.pack(side="left", fill="y", padx=(0, 15))

        ctk.CTkLabel(left_frame, text="配置各区域字体", font=("Microsoft YaHei", 14, "bold")).pack(anchor="w", pady=(10, 10))

        font_configs = [
            ("报告大标题与栏目", "font_header"),
            ("新闻条目小标题", "font_article"),
            ("情报摘要与正文", "font_body"),
            ("重点关注关键词", "font_keywords"),
            ("元数据与链接等宽", "font_accent")
        ]

        for label_text, config_key in font_configs:
            row_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=6)
            ctk.CTkLabel(row_frame, text=label_text, font=("Microsoft YaHei", 13)).pack(side="left")
            current_font = self.config.get(config_key, "")
            var = ctk.StringVar(value=current_font if current_font in self.font_list else "(系统默认)")
            self.font_vars[config_key] = var
            ctk.CTkOptionMenu(row_frame, values=self.font_list, variable=var, font=("Microsoft YaHei", 12), width=180, command=self.update_preview).pack(side="right")

        ctk.CTkFrame(left_frame, height=2, fg_color="#E0E0E0").pack(fill="x", pady=20)

        # 预览缩放
        zoom_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        zoom_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(zoom_frame, text="预览缩放 (Zoom)", font=("Microsoft YaHei", 14, "bold")).pack(side="left")
        self.lbl_zoom_val = ctk.CTkLabel(zoom_frame, text="1.0x", font=("Consolas", 14, "bold"), text_color="#008CBA")
        self.lbl_zoom_val.pack(side="right", padx=5)
        self.zoom_slider = ctk.CTkSlider(left_frame, from_=0.5, to=3.0, number_of_steps=25, command=self.on_zoom_change)
        self.zoom_slider.set(1.0)
        self.zoom_slider.pack(fill="x", pady=(0, 10))

        # 右侧预览
        right_frame = ctk.CTkFrame(main_frame, fg_color="#FFFFFF", border_width=1, border_color="#D5DBDB", corner_radius=8)
        right_frame.pack(side="right", fill="both", expand=True)
        ctk.CTkLabel(right_frame, text="排版预览 (WYSIWYG)", font=("Microsoft YaHei", 12, "bold"), text_color="gray").pack(pady=(10, 0))
        self.preview_text = tk.Text(right_frame, wrap="word", bg="#FFFFFF", fg="#333333", bd=0, highlightthickness=0, padx=25, pady=20)
        self.preview_text.pack(fill="both", expand=True)

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=15)
        ctk.CTkButton(bottom_frame, text="保存设置", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", width=120, command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", width=80, command=self.destroy).pack(side="right")

    def update_preview(self, *args):
        z = self.zoom_factor
        hf, hw, hs = self._analyze_font_file(self.font_vars["font_header"].get())
        af, aw, as_ = self._analyze_font_file(self.font_vars["font_article"].get())
        bf, bw, bs = self._analyze_font_file(self.font_vars["font_body"].get())
        kf, kw, ks = self._analyze_font_file(self.font_vars["font_keywords"].get())
        mf, mw, ms = self._analyze_font_file(self.font_vars["font_accent"].get())

        self.preview_text.tag_config("h1", font=(hf, int(20*z), hw, hs), foreground="#2C3E50", spacing3=int(10*z))
        self.preview_text.tag_config("blockquote", font=(bf, int(10*z), bs), foreground="#555555", background="#EBF5FB", lmargin1=int(15*z), lmargin2=int(15*z), spacing1=int(4*z), spacing3=int(4*z))
        self.preview_text.tag_config("h2", font=(hf, int(16*z), hw, hs), foreground="#2C3E50", spacing1=int(20*z), spacing3=int(10*z))
        self.preview_text.tag_config("h3", font=(af, int(14*z), aw, as_), foreground="#34495E", spacing1=int(15*z), spacing3=int(5*z))
        self.preview_text.tag_config("body", font=(bf, int(11*z), bw, bs), foreground="#333333", spacing1=int(5*z))
        self.preview_text.tag_config("keyword", font=(kf, int(11*z), kw, ks), foreground="#D32F2F")
        self.preview_text.tag_config("metadata", font=(mf, int(9*z), mw, ms), foreground="#7F8C8D", background="#E8ECEF")
        self.preview_text.tag_config("link", font=(mf, int(10*z), ms), foreground="#2980B9", underline=True)
        self.preview_text.tag_config("hr", foreground="#E0E0E0", justify="center", spacing1=int(10*z), spacing3=int(10*z))

        self.preview_text.config(state="normal")
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("end", "📡 全球新闻 AI 监听简报\n", "h1")
        self.preview_text.insert("end", f"> 🧠 生成模型：Local Ollama | Qwen3.5-30B\n", "blockquote")
        self.preview_text.insert("end", f"> 🕒 截获时间：2026-05-01 12:00\n", "blockquote")
        self.preview_text.insert("end", "📑 栏目导航\n", "h2")
        self.preview_text.insert("end", "• 世界 World\n", "link")
        self.preview_text.insert("end", "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n", "hr")
        self.preview_text.insert("end", "世界 World\n", "h2")
        self.preview_text.insert("end", "### [⭐] 这是一个示例标题\n", "h3")
        self.preview_text.insert("end", "• Title: This is an example title\n", "body")
        self.preview_text.insert("end", "• 关键词: ", "body")
        self.preview_text.insert("end", "示例\n", "keyword")
        self.preview_text.insert("end", "• 情报: ", "body")
        self.preview_text.insert("end", "This is an example content for font-preview\n", "body")
        self.preview_text.insert("end", "• 📎 元数据: ", "metadata")
        self.preview_text.insert("end", "栏目 [世界 World] | 来源 Example | 时间 2026-05-01 23:59 | 🔗 原文链接\n", "metadata")
        self.preview_text.config(state="disabled")

    def save_data(self):
        # 🌟 不再从 UI 读取语言，仅保存字体
        for config_key, var in self.font_vars.items():
            val = var.get()
            self.config[config_key] = "" if val == "(系统默认)" else val
        ConfigManager.save_config(self.config)
        self.destroy()