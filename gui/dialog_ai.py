import os
import threading
import tkinter as tk
import customtkinter as ctk
import tkinter.messagebox as messagebox
import requests
from openai import OpenAI
from core.config_mgr import ConfigManager
from .ui_utils import ToolTip

class AIModelDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI大模型及网络设置")
        # 🌟 窗口整体变窄，更加紧凑
        self.geometry("840x650") 
        self.grab_set()
        self.config = ConfigManager.load_config()
        self.real_api_key = ""
        self.is_key_visible = False
        self.placeholder = "AI，经济，能源，就业，......"
        
        self.is_multi_mode = self.config.get("is_multi_mode", False)
        self.multi_apis = self.config.get("multi_apis", [])
        self.current_api_index = 0
        
        self.api_test_status = [0] * max(len(self.multi_apis), 1)
        
        if not self.multi_apis:
            default_prov = self.config.get('ai_provider', 'Google Gemini')
            tpl = self.config.get('providers', {}).get(default_prov, {})
            self.multi_apis = [{
                'provider': default_prov,
                'url': tpl.get('url', ''),
                'model': tpl.get('model', ''),
                'api_key': tpl.get('api_key', '')
            }]

        self.init_ui()
        self.load_slot_to_form(0)

    def init_ui(self):
        ctk.CTkLabel(self, text="AI大模型及并发引擎设置", font=("Microsoft YaHei", 24, "bold")).pack(pady=10)

        main_layout = ctk.CTkFrame(self, fg_color="transparent")
        main_layout.pack(fill="both", expand=True, padx=20, pady=5)

        # ==================================================
        # 🌟 上半区 (表单 + 推拉门)
        # ==================================================
        top_section = ctk.CTkFrame(main_layout, fg_color="transparent")
        top_section.pack(fill="x", pady=5)

        # --- 左侧：核心参数 ---
        self.form_frame = ctk.CTkFrame(top_section, fg_color="transparent")
        self.form_frame.pack(side="left", fill="both", expand=True, padx=(0, 5)) # 🌟 缩小与右侧的间距

        tab_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        tab_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(tab_frame, text="选择服务商:", font=("Microsoft YaHei", 14, "bold")).pack(side="left", padx=5)
        self.provider_var = ctk.StringVar()
        self.provider_menu = ctk.CTkOptionMenu(
            tab_frame, values=list(self.config['providers'].keys()),
            variable=self.provider_var, command=self.on_provider_change, 
            font=("Microsoft YaHei", 14), width=180
        )
        self.provider_menu.pack(side="left", padx=5)

        params_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        params_box.pack(fill="x", pady=5)
        
        ctk.CTkLabel(params_box, text="模型URL", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        # 🌟 缩小输入框宽度以实现紧凑布局
        self.url_entry = ctk.CTkEntry(params_box, width=380, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.url_entry.grid(row=0, column=1, pady=10, sticky="w")

        ctk.CTkLabel(params_box, text="模型名称", font=("Microsoft YaHei", 14)).grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.name_entry = ctk.CTkEntry(params_box, width=380, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.name_entry.grid(row=1, column=1, pady=10, sticky="w")

        ctk.CTkLabel(params_box, text="API Key", font=("Microsoft YaHei", 14)).grid(row=2, column=0, padx=10, pady=10, sticky="e")
        key_subframe = ctk.CTkFrame(params_box, fg_color="transparent")
        key_subframe.grid(row=2, column=1, pady=10, sticky="w")
        
        self.key_entry = ctk.CTkEntry(key_subframe, width=190, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.key_entry.pack(side="left")
        self.key_entry.bind("<FocusIn>", self.on_key_focus_in)
        self.key_entry.bind("<FocusOut>", self.on_key_focus_out)
        
        self.btn_eye = ctk.CTkButton(key_subframe, text="🔒", width=35, font=("Microsoft YaHei", 16), fg_color="#B0B0B0", text_color="black", hover_color="#909090", command=self.toggle_key_visibility)
        self.btn_eye.pack(side="left", padx=5)
        
        self.btn_test_single = ctk.CTkButton(key_subframe, text="连接测试", font=("Microsoft YaHei", 14, "bold"), fg_color="#FF9800", text_color="black", hover_color="#F57C00", command=self.run_single_test)
        self.btn_test_single.pack(side="left", padx=5)

        proxy_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        proxy_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(proxy_frame, text="网络代理", font=("Microsoft YaHei", 14)).pack(side="left", padx=(10, 5))
        self.proxy_switch = ctk.CTkSwitch(proxy_frame, text="开启", font=("Microsoft YaHei", 14, "bold"), command=self.toggle_proxy)
        self.proxy_switch.pack(side="left", padx=5)
        if self.config.get('ai_use_proxy', False): self.proxy_switch.select()

        self.proxy_server_entry = ctk.CTkEntry(proxy_frame, width=150, font=("Microsoft YaHei", 14))
        self.proxy_server_entry.pack(side="left", padx=5)
        self.proxy_server_entry.insert(0, self.config.get('ai_proxy_server', 'http://127.0.0.1'))
        ctk.CTkLabel(proxy_frame, text=":", font=("Microsoft YaHei", 16, "bold")).pack(side="left")
        self.proxy_port_entry = ctk.CTkEntry(proxy_frame, width=70, font=("Microsoft YaHei", 14))
        self.proxy_port_entry.pack(side="left", padx=5)
        self.proxy_port_entry.insert(0, self.config.get('ai_proxy_port', '10808'))
        self.toggle_proxy()

        # --- 右侧：推拉门区 ---
        self.right_wrapper = ctk.CTkFrame(top_section, fg_color="transparent")
        self.right_wrapper.pack(side="right", anchor="n", pady=5)

        self.right_panel = ctk.CTkFrame(self.right_wrapper, width=160, height=210, fg_color="#E0E0E0", corner_radius=10)
        self.right_panel.pack(side="top")
        self.right_panel.pack_propagate(False)

        self.btn_test_all = ctk.CTkButton(self.right_wrapper, text="一键测试所有 API", font=("Microsoft YaHei", 13, "bold"), fg_color="#FF9800", text_color="black", hover_color="#F57C00", height=30, command=self.run_multi_test)

        self.render_door_panel()

        # ==================================================
        # 🌟 下半区 (批次 + 提示词) 
        # ==================================================
        bottom_section = ctk.CTkFrame(main_layout, fg_color="transparent")
        bottom_section.pack(fill="both", expand=True, pady=(5, 0)) 

        batch_subframe = ctk.CTkFrame(bottom_section, fg_color="transparent")
        batch_subframe.pack(fill="x", pady=5)
        ctk.CTkLabel(batch_subframe, text="单次向AI发送数量", font=("Microsoft YaHei", 14)).pack(side="left", padx=(10, 5))
        self.batch_entry = ctk.CTkEntry(batch_subframe, width=60, font=("Microsoft YaHei", 14))
        self.batch_entry.pack(side="left", padx=5)
        self.batch_entry.insert(0, str(self.config.get('batch_size', '30')))
        ctk.CTkLabel(batch_subframe, text="(小模型建议改小)", font=("Microsoft YaHei", 12), text_color="gray").pack(side="left", padx=5)

        prompt_subframe = ctk.CTkFrame(bottom_section, fg_color="transparent")
        prompt_subframe.pack(fill="both", expand=True, pady=(5, 0))
        ctk.CTkLabel(prompt_subframe, text="重点关注提示词 (打星标 ⭐):", font=("Microsoft YaHei", 13, "bold")).pack(anchor="w", padx=10, pady=(5,0))
        
        self.prompt_text = ctk.CTkTextbox(prompt_subframe, height=110, font=("Microsoft YaHei", 14), border_color="#008CBA", border_width=2)
        self.prompt_text.pack(fill="both", expand=True, padx=10, pady=(5, 0)) 
        
        saved_prompt = self.config.get('user_prompt', '').strip()
        if saved_prompt: self.prompt_text.insert("1.0", saved_prompt)
        else:
            self.prompt_text.insert("1.0", self.placeholder)
            self.prompt_text.configure(text_color="gray", font=("Microsoft YaHei", 14, "italic"))
        self.prompt_text.bind("<FocusIn>", self.on_prompt_focus_in)
        self.prompt_text.bind("<FocusOut>", self.on_prompt_focus_out)

        # --- 底部保存按钮 ---
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=40, pady=(10, 15))
        
        self.lbl_test_result = ctk.CTkLabel(bottom_frame, text="", font=("Microsoft YaHei", 14, "bold"))
        self.lbl_test_result.pack(side="left", padx=20)
        ctk.CTkButton(bottom_frame, text="保存所有配置", font=("Microsoft YaHei", 14, "bold"), fg_color="#008CBA", hover_color="#006b8f", width=140, command=self.save_data).pack(side="right", padx=10)
        ctk.CTkButton(bottom_frame, text="取消", font=("Microsoft YaHei", 14), fg_color="#B0B0B0", text_color="black", hover_color="#909090", width=80, command=self.destroy).pack(side="right")

    def get_slot_appearance(self, index):
        status = self.api_test_status[index]
        is_selected = (index == self.current_api_index)
        
        bg_color = "#FFFFFF"   
        text_color = "#000000"
        
        if status == 1:
            bg_color = "#4CAF50" 
            text_color = "#FFFFFF"
        elif status == -1:
            bg_color = "#F44336" 
            text_color = "#FFFFFF"

        border_width = 3 if is_selected else 1
        border_color = "#008CBA" if is_selected else "#A0A0A0"
        
        return bg_color, text_color, border_width, border_color

    def render_door_panel(self):
        for widget in self.right_panel.winfo_children():
            widget.destroy()

        if not self.is_multi_mode:
            self.btn_test_all.pack_forget()

            slot_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
            slot_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)
            
            bg, tc, bw, bc = self.get_slot_appearance(0)
            btn_1 = ctk.CTkButton(slot_frame, text="1", width=30, height=30, font=("Microsoft YaHei", 14, "bold"),
                                  fg_color=bg, text_color=tc, border_width=bw, border_color=bc, hover_color=bg)
            btn_1.pack(pady=5)
            
            door_text = "单\n模\n式\n\n▶\n切\n换"
            door_btn = ctk.CTkButton(self.right_panel, text=door_text, command=self.toggle_mode,
                                     width=30, 
                                     fg_color="#B0BEC5", text_color="#333", hover_color="#90A4AE", font=("Microsoft YaHei", 14, "bold"), corner_radius=8)
            door_btn.pack(side="right", fill="y", padx=(0, 5), pady=5)
        else:
            self.btn_test_all.pack(side="top", fill="x", pady=(10, 0))

            door_text = "多\n模\n式\n\n◀\n切\n换"
            door_btn = ctk.CTkButton(self.right_panel, text=door_text, command=self.toggle_mode,
                                     width=30, 
                                     fg_color="#81C784", text_color="#000", hover_color="#66BB6A", font=("Microsoft YaHei", 14, "bold"), corner_radius=8)
            door_btn.pack(side="left", fill="y", padx=(5, 0), pady=5)

            grid_frame = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent", width=110)
            grid_frame.pack(side="right", fill="both", expand=True, padx=(2, 5), pady=5)

            row, col = 0, 0
            for i in range(len(self.multi_apis)):
                bg, tc, bw, bc = self.get_slot_appearance(i)
                btn = ctk.CTkButton(grid_frame, text=str(i+1), width=30, height=30, font=("Microsoft YaHei", 14, "bold"), 
                                    fg_color=bg, text_color=tc, border_width=bw, border_color=bc, hover_color=bg,
                                    command=lambda idx=i: self.switch_api_slot(idx))
                btn.grid(row=row, column=col, padx=4, pady=4)
                col += 1
                if col > 1:
                    col = 0
                    row += 1
            
            ctrl_row = row + 1
            btn_add = ctk.CTkButton(grid_frame, text="➕", width=30, height=30, font=("Microsoft YaHei", 14, "bold"), fg_color="#4CAF50", hover_color="#45a049", command=self.add_api_slot)
            btn_add.grid(row=ctrl_row, column=0, padx=4, pady=8)
            
            btn_rm = ctk.CTkButton(grid_frame, text="➖", width=30, height=30, font=("Microsoft YaHei", 14, "bold"), fg_color="#F44336", hover_color="#D32F2F", command=self.remove_api_slot)
            btn_rm.grid(row=ctrl_row, column=1, padx=4, pady=8)

    def toggle_mode(self):
        self.save_current_slot_to_memory()
        self.is_multi_mode = not self.is_multi_mode
        if not self.is_multi_mode:
            self.load_slot_to_form(0)
        self.render_door_panel()

    def add_api_slot(self):
        self.save_current_slot_to_memory()
        
        default_prov = self.config.get('ai_provider', 'Google Gemini')
        tpl = self.config.get('providers', {}).get(default_prov, {})
        new_api = {
            'provider': default_prov,
            'url': tpl.get('url', ''),
            'model': tpl.get('model', ''),
            'api_key': ''  
        }
        
        self.multi_apis.append(new_api)
        self.api_test_status.append(0) 
        self.load_slot_to_form(len(self.multi_apis) - 1)

    def remove_api_slot(self):
        if len(self.multi_apis) > 1:
            self.multi_apis.pop(self.current_api_index)
            self.api_test_status.pop(self.current_api_index)
            new_idx = min(self.current_api_index, len(self.multi_apis) - 1)
            self.load_slot_to_form(new_idx)

    def switch_api_slot(self, index):
        self.save_current_slot_to_memory()
        self.load_slot_to_form(index)

    def save_current_slot_to_memory(self):
        self._sync_real_key_from_entry()
        self.multi_apis[self.current_api_index] = {
            'provider': self.provider_var.get(),
            'url': self.url_entry.get().strip(),
            'model': self.name_entry.get().strip(),
            'api_key': self.real_api_key
        }

    def load_slot_to_form(self, index):
        self.current_api_index = index
        data = self.multi_apis[index]
        
        self.provider_var.set(data.get('provider', 'Google Gemini'))
        self.url_entry.delete(0, 'end'); self.url_entry.insert(0, data.get('url', ''))
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, data.get('model', ''))
        self.real_api_key = data.get('api_key', '')
        
        self.is_key_visible = False
        self.btn_eye.configure(text="🔒")
        self.key_entry.configure(show="")
        self.key_entry.delete(0, 'end')
        if self.real_api_key:
            self.key_entry.insert(0, "●" * 20)
            
        self.render_door_panel() 

    def on_provider_change(self, new_provider):
        tpl = self.config.get('providers', {}).get(new_provider, {})
        self.url_entry.delete(0, 'end'); self.url_entry.insert(0, tpl.get('url', ''))
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, tpl.get('model', ''))

    def run_single_test(self):
        self.save_current_slot_to_memory()
        self.btn_test_single.configure(state="disabled", text="测试中...")
        self.lbl_test_result.configure(text=f"正在检测 API-{self.current_api_index + 1}...", text_color="black")
        
        api_data = self.multi_apis[self.current_api_index]
        use_proxy = bool(self.proxy_switch.get())
        proxy_str = f"{self.proxy_server_entry.get()}:{self.proxy_port_entry.get()}" if use_proxy else None

        threading.Thread(target=self._perform_single_test, args=(api_data, self.current_api_index, proxy_str), daemon=True).start()

    def run_multi_test(self):
        self.save_current_slot_to_memory()
        self.lbl_test_result.configure(text="正在检测所有接口...", text_color="black")
        use_proxy = bool(self.proxy_switch.get())
        proxy_str = f"{self.proxy_server_entry.get()}:{self.proxy_port_entry.get()}" if use_proxy else None

        threading.Thread(target=self._perform_batch_test, args=(proxy_str,), daemon=True).start()

    def _test_core_logic(self, api):
        provider = api.get('provider')
        url = api.get('url')
        name = api.get('model')
        key = api.get('api_key')
        
        if not key: return False, "未填写 API Key"

        try:
            if provider == "Google Gemini":
                headers = {"Content-Type": "application/json"}
                data = {"contents": [{"parts": [{"text": "Reply 'OK'."}]}]}
                base = url.strip().rstrip('/')
                if not base.endswith('models'): base = f"{base}/models"
                full_url = f"{base}/{name}:generateContent?key={key}"
                resp = requests.post(full_url, headers=headers, json=data)
                resp.raise_for_status()
                res = resp.json()['candidates'][0]['content']['parts'][0]['text']
            elif provider == "Claude":
                headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                data = {"model": name, "max_tokens": 10, "messages": [{"role": "user", "content": "Reply 'OK'."}]}
                resp = requests.post(url, headers=headers, json=data)
                resp.raise_for_status()
                res = resp.json()['content'][0]['text']
            else:
                client = OpenAI(api_key=key, base_url=url)
                response = client.chat.completions.create(model=name, messages=[{"role": "user", "content": "Reply 'OK'."}])
                res = response.choices[0].message.content

            if res: return True, "OK"
            return False, "返回为空"
        except Exception as e:
            return False, str(e)[:30]

    def _perform_single_test(self, api_data, index, proxy_str):
        import os
        if proxy_str: os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_str, proxy_str
        else: os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)

        success, msg = self._test_core_logic(api_data)
        
        self.api_test_status[index] = 1 if success else -1
        
        self.after(0, self.render_door_panel)
        if success:
            self.after(0, self._show_result, True, f"✅ API-{index+1} 测试通过！")
        else:
            self.after(0, self._show_result, False, f"❌ API-{index+1} 失败: {msg}")

    def _perform_batch_test(self, proxy_str):
        import os
        if proxy_str: os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_str, proxy_str
        else: os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)

        all_success = True
        results_log = []

        for idx, api in enumerate(self.multi_apis):
            success, msg = self._test_core_logic(api)
            self.api_test_status[idx] = 1 if success else -1
            
            self.after(0, self.render_door_panel)
            
            if success:
                results_log.append(f"✅ API-{idx+1} [{api.get('provider')}]: 畅通")
            else:
                results_log.append(f"❌ API-{idx+1} [{api.get('provider')}]: {msg}")
                all_success = False

        summary = "\n".join(results_log)
        self.after(0, lambda: messagebox.showinfo(f"一键测试结果 ({len(self.multi_apis)}个)", summary))
        
        if all_success:
            self.after(0, self._show_result, True, f"✅ 全部 {len(self.multi_apis)} 个并发接口畅通！")
        else:
            self.after(0, self._show_result, False, f"⚠️ 部分接口异常，方块已标红。")

    def _show_result(self, is_success, msg):
        self.btn_test_single.configure(state="normal", text="连接测试")
        self.lbl_test_result.configure(text=msg, text_color="#4CAF50" if is_success else "#F44336")

    def save_data(self):
        self.save_current_slot_to_memory()
        
        self.config['is_multi_mode'] = self.is_multi_mode
        self.config['multi_apis'] = self.multi_apis
        
        self.config['ai_use_proxy'] = bool(self.proxy_switch.get())
        self.config['ai_proxy_server'] = self.proxy_server_entry.get()
        self.config['ai_proxy_port'] = self.proxy_port_entry.get()
        self.config['batch_size'] = self.batch_entry.get().strip()
        
        prompt_val = self.prompt_text.get("1.0", "end-1c").strip()
        if prompt_val == self.placeholder: prompt_val = ""
        self.config['user_prompt'] = prompt_val
        
        ConfigManager.save_config(self.config)
        self.destroy()

    def toggle_proxy(self):
        if self.proxy_switch.get():
            self.proxy_switch.configure(text="开启")
            self.proxy_server_entry.configure(state="normal", text_color="black")
            self.proxy_port_entry.configure(state="normal", text_color="black")
        else:
            self.proxy_switch.configure(text="关闭")
            self.proxy_server_entry.configure(state="disabled", text_color="gray")
            self.proxy_port_entry.configure(state="disabled", text_color="gray")

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