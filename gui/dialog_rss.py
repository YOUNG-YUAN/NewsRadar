import tkinter as tk
import customtkinter as ctk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
from core.config_mgr import ConfigManager

class RSSProxyDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("网络代理 (仅限RSS抓取)")
        self.geometry("450x180")
        self.grab_set()
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        proxy_frame = ctk.CTkFrame(self, fg_color="transparent")
        proxy_frame.pack(fill="x", padx=15, pady=30)
        
        ctk.CTkLabel(proxy_frame, text="网络代理", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=5)
        self.proxy_switch = ctk.CTkSwitch(proxy_frame, text="开启", font=("Microsoft YaHei", 14, "bold"), command=self.toggle_proxy)
        self.proxy_switch.grid(row=0, column=1, padx=5, pady=5)
        if self.config.get('rss_use_proxy', False): self.proxy_switch.select()

        self.proxy_server_entry = ctk.CTkEntry(proxy_frame, width=150, font=("Microsoft YaHei", 14))
        self.proxy_server_entry.grid(row=0, column=2, padx=5, pady=5)
        self.proxy_server_entry.insert(0, self.config.get('rss_proxy_server', 'http://127.0.0.1'))
        
        ctk.CTkLabel(proxy_frame, text=":", font=("Microsoft YaHei", 16, "bold")).grid(row=0, column=3)
        
        self.proxy_port_entry = ctk.CTkEntry(proxy_frame, width=70, font=("Microsoft YaHei", 14))
        self.proxy_port_entry.grid(row=0, column=4, padx=5, pady=5)
        self.proxy_port_entry.insert(0, self.config.get('rss_proxy_port', '10808'))

        self.toggle_proxy()

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=15)
        ctk.CTkButton(bottom_frame, text="保存", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", hover_color="#006b8f", command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", hover_color="#909090", command=self.destroy).pack(side="right")

    def toggle_proxy(self):
        if self.proxy_switch.get():
            self.proxy_switch.configure(text="开启")
            self.proxy_server_entry.configure(state="normal", text_color="black")
            self.proxy_port_entry.configure(state="normal", text_color="black")
        else:
            self.proxy_switch.configure(text="关闭")
            self.proxy_server_entry.configure(state="disabled", text_color="gray")
            self.proxy_port_entry.configure(state="disabled", text_color="gray")

    def save_data(self):
        self.config['rss_use_proxy'] = bool(self.proxy_switch.get())
        self.config['rss_proxy_server'] = self.proxy_server_entry.get()
        self.config['rss_proxy_port'] = self.proxy_port_entry.get()
        ConfigManager.save_config(self.config)
        self.destroy()

class ListenSettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("监听设置")
        self.geometry("900x600")
        self.grab_set()
        self.sources = ConfigManager.load_sources()
        self.config = ConfigManager.load_config()
        self.init_ui()

    def init_ui(self):
        ctk.CTkLabel(self, text="监听设置", font=("Microsoft YaHei", 24, "bold")).pack(pady=10)
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=40, pady=5)
        
        left_ctrl_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        left_ctrl_frame.pack(side="left", anchor="n") 
        
        btn_add = ctk.CTkButton(left_ctrl_frame, text="添加平台", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", hover_color="#006b8f", width=100, command=self.add_platform)
        btn_add.grid(row=0, column=0, sticky="n")
        
        btn_sel_all = ctk.CTkButton(left_ctrl_frame, text="一键全选", font=("Microsoft YaHei", 14, "bold"), fg_color="#4CAF50", hover_color="#45a049", width=100, command=self.select_all)
        btn_sel_all.grid(row=0, column=1, padx=10, sticky="n") 
        
        btn_desel_all = ctk.CTkButton(left_ctrl_frame, text="全部取消", font=("Microsoft YaHei", 14, "bold"), fg_color="#FFEB3B", text_color="black", hover_color="#FBC02D", width=100, command=self.deselect_all)
        btn_desel_all.grid(row=0, column=2, sticky="n")
        
        btn_proxy = ctk.CTkButton(left_ctrl_frame, text="网络代理", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", text_color="white", width=100, command=self.open_proxy_settings)
        btn_proxy.grid(row=0, column=3, padx=10, sticky="n")
        
        self.lbl_proxy_status = ctk.CTkLabel(left_ctrl_frame, text="", font=("Microsoft YaHei", 11, "bold"), text_color="#008CBA", height=14)
        self.lbl_proxy_status.grid(row=1, column=3, pady=(2, 0), sticky="n")
        
        if self.config.get('rss_use_proxy', False):
            self.lbl_proxy_status.configure(text="已开启代理")
        
        freq_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        freq_frame.pack(side="right", anchor="n")
        ctk.CTkLabel(freq_frame, text="监听频率:", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=(0, 5))
        
        self.entry_d = ctk.CTkEntry(freq_frame, width=40, font=("Microsoft YaHei", 14))
        self.entry_d.pack(side="left")
        ctk.CTkLabel(freq_frame, text="d", font=("Microsoft YaHei", 14)).pack(side="left", padx=(2, 10))
        self.entry_h = ctk.CTkEntry(freq_frame, width=40, font=("Microsoft YaHei", 14))
        self.entry_h.pack(side="left")
        ctk.CTkLabel(freq_frame, text="h", font=("Microsoft YaHei", 14)).pack(side="left", padx=(2, 10))
        self.entry_m = ctk.CTkEntry(freq_frame, width=40, font=("Microsoft YaHei", 14))
        self.entry_m.pack(side="left")
        ctk.CTkLabel(freq_frame, text="min", font=("Microsoft YaHei", 14)).pack(side="left", padx=(2, 0))

        self.load_frequency_to_ui()

        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=40, pady=(0, 5))
        self.switch_fetch = ctk.CTkSwitch(mode_frame, text="当前周期的新闻", font=("Microsoft YaHei", 14, "bold"), command=self.toggle_fetch_mode)
        self.switch_fetch.pack(side="right", padx=5)
        if self.config.get('fetch_all', False):
            self.switch_fetch.select()
            self.switch_fetch.configure(text="RSS下所有新闻")

        table_container = ctk.CTkFrame(self)
        table_container.pack(fill="both", expand=True, padx=40, pady=5)
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", background="white", foreground="black", rowheight=35, fieldbackground="white", font=('Microsoft YaHei', 12), borderwidth=1)
        style.map('Treeview', background=[('selected', '#008CBA')], foreground=[('selected', 'white')])
        style.configure("Treeview.Heading", background="#F0F0F0", foreground="black", font=('Microsoft YaHei', 13, 'bold'))

        self.tree = ttk.Treeview(table_container, columns=("check", "name", "url", "note"), show="headings", selectmode="browse")
        self.tree.heading("check", text="选取"); self.tree.heading("name", text="平台名称")
        self.tree.heading("url", text="RSS来源"); self.tree.heading("note", text="备注")
        self.tree.column("check", width=60, anchor="center"); self.tree.column("name", width=140)
        self.tree.column("url", width=400); self.tree.column("note", width=150)
        
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        
        self.tree.bind("<Delete>", self.delete_platform)
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<ButtonRelease-1>", self.on_single_click)

        self.load_table()

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=40, pady=10)
        ctk.CTkButton(bottom_frame, text="保存", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", command=self.destroy).pack(side="right")

    def open_proxy_settings(self):
        RSSProxyDialog(self).wait_window()
        self.config = ConfigManager.load_config()
        if self.config.get('rss_use_proxy', False):
            self.lbl_proxy_status.configure(text="已开启代理")
        else:
            self.lbl_proxy_status.configure(text="")

    def toggle_fetch_mode(self):
        self.switch_fetch.configure(text="RSS下所有新闻" if self.switch_fetch.get() else "当前周期的新闻")

    def load_frequency_to_ui(self):
        freq_str = self.config.get('listen_freq', '1h')
        total_mins = 60
        try:
            val, unit = int(freq_str[:-1]), freq_str[-1].lower()
            if unit == 'm': total_mins = val
            elif unit == 'h': total_mins = val * 60
            elif unit == 'd': total_mins = val * 24 * 60
        except: pass
        self.entry_d.insert(0, str(total_mins // (24 * 60)))
        self.entry_h.insert(0, str((total_mins % (24 * 60)) // 60))
        self.entry_m.insert(0, str(total_mins % 60))

    def get_frequency_from_ui(self):
        try:
            d = int(self.entry_d.get() or 0)
            h = int(self.entry_h.get() or 0)
            m = int(self.entry_m.get() or 0)
            total_mins = max(d * 24 * 60 + h * 60 + m, 60)
            return f"{total_mins}m"
        except ValueError: return None

    def select_all(self):
        for src in self.sources: src['checked'] = True
        self.load_table()

    def deselect_all(self):
        for src in self.sources: src['checked'] = False
        self.load_table()

    def load_table(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for i, src in enumerate(self.sources):
            self.tree.insert("", "end", iid=str(i), values=("☑" if src.get('checked', True) else "☐", src['name'], src['url'], src.get('note', '')))

    def on_single_click(self, event):
        if self.tree.identify("region", event.x, event.y) == "cell" and self.tree.identify_column(event.x) == "#1": 
            if iid := self.tree.focus():
                self.sources[int(iid)]['checked'] = not self.sources[int(iid)].get('checked', True)
                self.load_table()

    def delete_platform(self, event):
        if iid := self.tree.focus():
            if messagebox.askyesno("确认", "确认要删除该新闻平台吗？"):
                self.sources.pop(int(iid)); self.load_table()

    def on_double_click(self, event):
        if iid := self.tree.focus(): self.edit_dialog(int(iid))

    def add_platform(self): self.edit_dialog(None)

    def edit_dialog(self, index):
        dlg = ctk.CTkToplevel(self)
        dlg.title("添加/编辑平台")
        dlg.geometry("600x300")
        dlg.grab_set()

        form = ctk.CTkFrame(dlg, fg_color="transparent")
        form.pack(fill="x", padx=30, pady=30)
        ctk.CTkLabel(form, text="平台名称", font=("Microsoft YaHei", 13)).grid(row=0, column=0, padx=10, pady=10)
        name_entry = ctk.CTkEntry(form, width=400, font=("Microsoft YaHei", 13), border_color="#008CBA", border_width=2); name_entry.grid(row=0, column=1)
        ctk.CTkLabel(form, text="RSS来源", font=("Microsoft YaHei", 13)).grid(row=1, column=0, padx=10, pady=10)
        url_entry = ctk.CTkEntry(form, width=400, font=("Microsoft YaHei", 13), border_color="#008CBA", border_width=2); url_entry.grid(row=1, column=1)
        ctk.CTkLabel(form, text="备注", font=("Microsoft YaHei", 13)).grid(row=2, column=0, padx=10, pady=10)
        note_entry = ctk.CTkEntry(form, width=400, font=("Microsoft YaHei", 13), border_color="#008CBA", border_width=2); note_entry.grid(row=2, column=1)

        if index is not None:
            name_entry.insert(0, self.sources[index]['name'])
            url_entry.insert(0, self.sources[index]['url'])
            note_entry.insert(0, self.sources[index].get('note', ''))

        def save_edit():
            new_data = {"checked": True, "name": name_entry.get(), "url": url_entry.get(), "note": note_entry.get()}
            if index is not None: self.sources[index] = new_data
            else: self.sources.append(new_data)
            self.load_table(); dlg.destroy()

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack(fill="x", padx=30, pady=10)
        ctk.CTkButton(btns, text="确认", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", command=save_edit).pack(side="right", padx=10)
        ctk.CTkButton(btns, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", command=dlg.destroy).pack(side="right")

    def save_data(self):
        new_freq = self.get_frequency_from_ui()
        if not new_freq:
            messagebox.showwarning("格式错误", "频率只能输入整数！")
            return
        ConfigManager.save_sources(self.sources)
        self.config['listen_freq'] = new_freq
        self.config['fetch_all'] = bool(self.switch_fetch.get())
        ConfigManager.save_config(self.config)
        self.destroy()