import threading
import tkinter as tk
import customtkinter as ctk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox
from core.config_mgr import ConfigManager
import google.generativeai as genai
from openai import OpenAI
import requests

# 🌟 新增：轻量级悬浮提示气泡类
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = event.x_root + 15
        y = event.y_root + 10
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#2B2B2B", foreground="white",
                         relief='solid', borderwidth=1,
                         font=("Microsoft YaHei", 11), wraplength=450)
        label.pack(ipadx=10, ipady=6)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


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
        self.name_entry.insert(0, "NewsSummary_YYYY-MM-DD-HHMM.md")
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
        ConfigManager.save_config(self.config)
        self.destroy()

class AIModelDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI大模型及网络设置")
        
        # 🌟 核心修改：将原本的 "800x720" 缩减为 "800x640"，完美消除底部多余空白
        self.geometry("800x640") 
        
        self.grab_set()
        self.config = ConfigManager.load_config()
        self.real_api_key = ""
        self.is_key_visible = False
        self.placeholder = "AI，经济，能源，就业，......"
        self.init_ui()

    def init_ui(self):
        ctk.CTkLabel(self, text="AI大模型及网络设置", font=("Microsoft YaHei", 24, "bold")).pack(pady=15)

        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=40, pady=5)
        
        ctk.CTkLabel(tab_frame, text="选择服务商:", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=5)
        self.provider_var = ctk.StringVar(value=self.config.get('ai_provider', 'Google Gemini'))
        self.provider_menu = ctk.CTkOptionMenu(
            tab_frame, values=list(self.config['providers'].keys()),
            variable=self.provider_var, command=self.switch_provider, 
            font=("Microsoft YaHei", 14), width=200
        )
        self.provider_menu.pack(side="left", padx=5)

        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=40, pady=10)

        # === 1. 模型表单区 ===
        form_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        form_frame.pack(fill="x", pady=5)
        
        ctk.CTkLabel(form_frame, text="模型URL", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.url_entry = ctk.CTkEntry(form_frame, width=500, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.url_entry.grid(row=0, column=1, pady=10, sticky="w")

        ctk.CTkLabel(form_frame, text="模型名称", font=("Microsoft YaHei", 14)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(form_frame, width=500, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.name_entry.grid(row=1, column=1, pady=10, sticky="w")

        ctk.CTkLabel(form_frame, text="API Key", font=("Microsoft YaHei", 14)).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        
        key_subframe = ctk.CTkFrame(form_frame, fg_color="transparent")
        key_subframe.grid(row=2, column=1, pady=10, sticky="w")
        
        self.key_entry = ctk.CTkEntry(key_subframe, width=280, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.key_entry.pack(side="left")
        self.key_entry.bind("<FocusIn>", self.on_key_focus_in)
        self.key_entry.bind("<FocusOut>", self.on_key_focus_out)
        
        self.btn_eye = ctk.CTkButton(key_subframe, text="🔒", width=40, font=("Microsoft YaHei", 16), fg_color="#B0B0B0", text_color="black", hover_color="#909090", command=self.toggle_key_visibility)
        self.btn_eye.pack(side="left", padx=10)
        
        self.btn_test = ctk.CTkButton(key_subframe, text="连接测试", font=("Microsoft YaHei", 14, "bold"), fg_color="#FF9800", text_color="black", hover_color="#F57C00", command=self.run_test_in_bg)
        self.btn_test.pack(side="left", padx=5)

        # === 2. 网络代理区 ===
        proxy_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        proxy_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(proxy_frame, text="网络代理", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.proxy_switch = ctk.CTkSwitch(proxy_frame, text="开启", font=("Microsoft YaHei", 14, "bold"), command=self.toggle_proxy)
        self.proxy_switch.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        if self.config.get('ai_use_proxy', False): self.proxy_switch.select()

        self.proxy_server_entry = ctk.CTkEntry(proxy_frame, width=200, font=("Microsoft YaHei", 14))
        self.proxy_server_entry.grid(row=0, column=2, padx=5, pady=5)
        self.proxy_server_entry.insert(0, self.config.get('ai_proxy_server', 'http://127.0.0.1'))
        ctk.CTkLabel(proxy_frame, text=":", font=("Microsoft YaHei", 16, "bold")).grid(row=0, column=3)
        self.proxy_port_entry = ctk.CTkEntry(proxy_frame, width=80, font=("Microsoft YaHei", 14))
        self.proxy_port_entry.grid(row=0, column=4, padx=5, pady=5)
        self.proxy_port_entry.insert(0, self.config.get('ai_proxy_port', '10808'))

        self.toggle_proxy()
        
        test_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        test_frame.pack(fill="x", padx=80, pady=0)
        self.lbl_test_result = ctk.CTkLabel(test_frame, text="", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_test_result.pack(side="left", padx=20)

        # === 3. 🌟 新增：系统参数与提示词区 ===
        params_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        params_frame.pack(fill="x", pady=10)

        # 批次大小设置
        batch_subframe = ctk.CTkFrame(params_frame, fg_color="transparent")
        batch_subframe.pack(fill="x", pady=5)
        
        lbl_batch = ctk.CTkLabel(batch_subframe, text="单次向AI大模型发送的新闻条目数量", font=("Microsoft YaHei", 14))
        lbl_batch.pack(side="left", padx=(10, 5))
        
        # 绑定气泡提示
        ToolTip(lbl_batch, "该值过低可能导致每分钟的请求次数过多超过限额从而请求失败的情况。\n但是过高容易出现AI大模型处理不过来，生成的条目不全的情况。\n对于本地部署的小模型，不受请求频率的限制，可以把值改小一些，比如8。")
        
        self.batch_entry = ctk.CTkEntry(batch_subframe, width=60, font=("Microsoft YaHei", 14))
        self.batch_entry.pack(side="left", padx=5)
        self.batch_entry.insert(0, str(self.config.get('batch_size', '30')))
        
        ctk.CTkLabel(batch_subframe, text="建议范围：20-40", font=("Microsoft YaHei", 12), text_color="gray").pack(side="left", padx=5)

        # 提示词设置
        prompt_subframe = ctk.CTkFrame(params_frame, fg_color="transparent")
        prompt_subframe.pack(fill="x", pady=5)
        
        ctk.CTkLabel(prompt_subframe, text="在下方输入的您特别关注的提示词，符合该提示词的新闻会被加星标（⭐）并移到栏目前面：", font=("Microsoft YaHei", 13, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        
        self.prompt_text = ctk.CTkTextbox(prompt_subframe, height=100, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.prompt_text.pack(fill="x", padx=10, pady=5)
        
        saved_prompt = self.config.get('user_prompt', '').strip()
        if saved_prompt:
            self.prompt_text.insert("1.0", saved_prompt)
        else:
            # 初始化占位符
            self.prompt_text.insert("1.0", self.placeholder)
            self.prompt_text.configure(text_color="gray", font=("Microsoft YaHei", 14, "italic"))
            
        self.prompt_text.bind("<FocusIn>", self.on_prompt_focus_in)
        self.prompt_text.bind("<FocusOut>", self.on_prompt_focus_out)

        # 加载下拉菜单数据
        self._load_provider_data(self.provider_var.get())

        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=40, pady=15)
        ctk.CTkButton(bottom_frame, text="保存", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", hover_color="#006b8f", command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", hover_color="#909090", command=self.destroy).pack(side="right")


    # ================== 🌟 提示词占位符逻辑 ==================
    def on_prompt_focus_in(self, event):
        text = self.prompt_text.get("1.0", "end-1c")
        if text == self.placeholder:
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.configure(text_color=["black", "white"], font=("Microsoft YaHei", 14, "normal"))

    def on_prompt_focus_out(self, event):
        text = self.prompt_text.get("1.0", "end-1c")
        if not text.strip():
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", self.placeholder)
            self.prompt_text.configure(text_color="gray", font=("Microsoft YaHei", 14, "italic"))

    # ================== API Key 视觉遮盖逻辑 ==================
    def _sync_real_key_from_entry(self):
        if self.focus_get() == self.key_entry:
            current_val = self.key_entry.get()
            if self.key_entry.cget("show") == "●" or current_val != "●" * 20:
                self.real_api_key = current_val

    def on_key_focus_in(self, event):
        if not self.is_key_visible:
            self.key_entry.delete(0, 'end')
            self.key_entry.insert(0, self.real_api_key)
            self.key_entry.configure(show="●")

    def on_key_focus_out(self, event):
        current_val = self.key_entry.get()
        if self.key_entry.cget("show") == "●" or current_val != "●" * 20:
            self.real_api_key = current_val

        if not self.is_key_visible:
            self.key_entry.configure(show="")
            self.key_entry.delete(0, 'end')
            if self.real_api_key:
                self.key_entry.insert(0, "●" * 20)

    def toggle_key_visibility(self):
        current_val = self.key_entry.get()
        if self.key_entry.cget("show") == "●" or current_val != "●" * 20:
            self.real_api_key = current_val

        self.is_key_visible = not self.is_key_visible

        if self.is_key_visible:
            self.btn_eye.configure(text="👁")
            self.key_entry.configure(show="")
            self.key_entry.delete(0, 'end')
            self.key_entry.insert(0, self.real_api_key)
        else:
            self.btn_eye.configure(text="🔒")
            self.key_entry.configure(show="")
            self.key_entry.delete(0, 'end')
            if self.real_api_key:
                self.key_entry.insert(0, "●" * 20)

    # ================== 核心设置逻辑 ==================
    def toggle_proxy(self):
        if self.proxy_switch.get():
            self.proxy_switch.configure(text="开启")
            self.proxy_server_entry.configure(state="normal", text_color="black")
            self.proxy_port_entry.configure(state="normal", text_color="black")
        else:
            self.proxy_switch.configure(text="关闭")
            self.proxy_server_entry.configure(state="disabled", text_color="gray")
            self.proxy_port_entry.configure(state="disabled", text_color="gray")

    def _save_current_provider_data(self):
        self._sync_real_key_from_entry()
        current = self.config.get('ai_provider', 'Google Gemini')
        self.config['providers'][current] = {
            "url": self.url_entry.get(),
            "model": self.name_entry.get(),
            "api_key": self.real_api_key
        }

    def _load_provider_data(self, provider):
        data = self.config['providers'].get(provider, {})
        self.url_entry.delete(0, 'end'); self.url_entry.insert(0, data.get('url', ''))
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, data.get('model', ''))
        
        self.real_api_key = data.get('api_key', '')
        
        self.is_key_visible = False
        self.btn_eye.configure(text="🔒")
        self.key_entry.configure(show="")
        self.key_entry.delete(0, 'end')
        if self.real_api_key:
            self.key_entry.insert(0, "●" * 20)

    def switch_provider(self, new_provider):
        self._save_current_provider_data()
        self.config['ai_provider'] = new_provider
        self.lbl_test_result.configure(text="") 
        self._load_provider_data(new_provider)

    def run_test_in_bg(self):
        self._sync_real_key_from_entry()
        self.btn_test.configure(state="disabled", text="测试中...")
        self.lbl_test_result.configure(text="", text_color="black")
        
        provider = self.provider_var.get()
        url = self.url_entry.get()
        name = self.name_entry.get()
        key = self.real_api_key
        use_proxy = bool(self.proxy_switch.get())
        proxy_str = f"{self.proxy_server_entry.get()}:{self.proxy_port_entry.get()}" if use_proxy else None

        threading.Thread(target=self._perform_test, args=(provider, url, name, key, proxy_str), daemon=True).start()

    def _perform_test(self, provider, url, name, key, proxy_str):
        import os
        try:
            if proxy_str:
                os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_str, proxy_str
            else:
                os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)

            if provider == "Google Gemini":
                genai.configure(api_key=key)
                model = genai.GenerativeModel(model_name=name)
                response = model.generate_content("Reply only the word 'OK'.")
                result_text = response.text
            elif provider == "Claude":
                headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                data = {"model": name, "max_tokens": 10, "messages": [{"role": "user", "content": "Reply only the word 'OK'."}]}
                resp = requests.post(url, headers=headers, json=data)
                resp.raise_for_status()
                result_text = resp.json()['content'][0]['text']
            else:
                client = OpenAI(api_key=key, base_url=url)
                response = client.chat.completions.create(
                    model=name, messages=[{"role": "user", "content": "Reply only the word 'OK'."}]
                )
                result_text = response.choices[0].message.content
                if not result_text and hasattr(response.choices[0].message, 'reasoning_content'):
                    result_text = response.choices[0].message.reasoning_content

            if result_text: self.after(0, self._show_result, True, f"✅ 成功! ({name})")
            else: self.after(0, self._show_result, False, "❌ 失败! (返回为空)")
                
        except Exception as e:
            self.after(0, self._show_result, False, f"❌ 失败! {str(e)[:50]}...")

    def _show_result(self, is_success, msg):
        self.btn_test.configure(state="normal", text="连接测试")
        self.lbl_test_result.configure(text=msg, text_color="#4CAF50" if is_success else "#F44336")

    def save_data(self):
        self._save_current_provider_data()
        self.config['ai_use_proxy'] = bool(self.proxy_switch.get())
        self.config['ai_proxy_server'] = self.proxy_server_entry.get()
        self.config['ai_proxy_port'] = self.proxy_port_entry.get()
        
        # 🌟 保存批次和提示词配置
        self.config['batch_size'] = self.batch_entry.get().strip()
        
        prompt_val = self.prompt_text.get("1.0", "end-1c").strip()
        if prompt_val == self.placeholder:
            prompt_val = ""
        self.config['user_prompt'] = prompt_val
        
        ConfigManager.save_config(self.config)
        self.destroy()

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