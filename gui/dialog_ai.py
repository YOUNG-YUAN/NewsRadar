import os
import threading
import customtkinter as ctk
import tkinter.messagebox as messagebox
from core.config_mgr import ConfigManager
from core.llm_client import call_llm, build_proxy
from core.prompts import build_connect_test_prompt
from .ui_utils import ToolTip


class ApiSquareButton(ctk.CTkButton):
    """原生 CTkButton 圆角方形 API 块（CustomTkinter 抗锯齿渲染，即"改之前的样式"）。

    编号与禁用时的红色 ✕ 都由内部 canvas 绘制（**不用** CTkButton 自带 label——
    它的不透明底色会挡住 ✕ 中央一大片）：先画 ✕ 再画编号，编号在 ✕ 上方、
    只占数字字形本身，不遮挡斜线主体。✕ 从 corner_radius-2 起笔（旧版为
    corner_radius+1），每端向外延伸约 20%、整体拉长约 40%，且仍落在圆角填充区内。
    覆写 _draw + 绑定 canvas <Configure>：布局缩放/尺寸变化后中心内容始终刷新
    （单靠 _draw 会在画布未完成 DPI 缩放时以过期尺寸绘制一次，之后不再触发）。"""
    def __init__(self, *args, disabled=False, **kwargs):
        self._api_disabled = bool(disabled)
        self._api_text = str(kwargs.get('text', ''))
        self._api_tc = kwargs.get('text_color', '#000000')
        kwargs['text'] = ''  # 弃用自带 label（不透明遮挡 ✕），编号改由 canvas 绘制
        self._api_inset = 10  # 兜底默认，super().__init__ 期间 _draw 即可能触发
        super().__init__(*args, **kwargs)
        self._api_inset = max(2, int(kwargs.get('corner_radius', 12) or 12) - 2)
        # 强制正方形：CTkButton 内部 grid 的圆角列 minsize 与 label 行高不等，
        # 高 DPI 缩放下会把按钮撑成 43×39 的长方形圆角（横边≠竖边）。
        # 关闭 grid 传播并给显式等宽高（34 逻辑单位 → 125% 缩放即 43×43），
        # 任意缩放下都保持正方形。
        self.pack_propagate(False)
        self.configure(width=34, height=34)
        self._canvas.bind("<Configure>", lambda e: self._draw_center_content(), add="+")

    def _draw(self, no_color_updates=False):
        super()._draw(no_color_updates)
        self._draw_center_content()

    def _draw_center_content(self):
        """在 canvas 上绘制中心内容：先 ✕（仅禁用时）后编号，编号在 ✕ 上方。"""
        try:
            cv = self._canvas
            cv.delete("api_center")
            w, h = cv.winfo_width(), cv.winfo_height()
            if w < 10 or h < 10:
                return
            if self._api_disabled:
                i = self._api_inset
                cv.create_line(i, i, w - i, h - i, fill="#F44336", width=2, tags="api_center")
                cv.create_line(w - i, i, i, h - i, fill="#F44336", width=2, tags="api_center")
            cv.create_text(w / 2, h / 2, text=self._api_text,
                           fill=self._api_tc, font=("Microsoft YaHei", 14, "bold"),
                           tags="api_center")
        except Exception:
            pass

class AIModelDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("AI大模型及网络设置")
        self.geometry("840x650") 
        self.grab_set()
        self.config = ConfigManager.load_config()
        self.real_api_key = ""
        self.is_key_visible = False
        self.placeholder = "AI，经济，能源，就业，......"
        
        self.is_multi_mode = self.config.get("is_multi_mode", False)
        self.multi_apis = self.config.get("multi_apis", [])
        self.current_api_index = 0
        
        # 🌟 独立提取单模式数据，彻底与 multi_apis 数组解绑
        default_prov = self.config.get('ai_provider', 'Google Gemini')
        tpl = self.config.get('providers', {}).get(default_prov, {})
        self.single_api = {
            'provider': default_prov,
            'url': tpl.get('url', ''),
            'model': tpl.get('model', ''),
            'api_key': tpl.get('api_key', ''),
            'enabled': self.config.get('single_api_enabled', True),  # 🌟 单模式 API 启用开关
            'disable_thinking': self.config.get('single_api_disable_thinking', False)  # 🌟 单模式禁用思考
        }
        self.single_test_status = 0 # 单模式专属状态

        # 🌟 兼容旧配置：multi_apis 无 enabled / disable_thinking 字段时取默认值
        for api in self.multi_apis:
            api.setdefault('enabled', True)
            api.setdefault('disable_thinking', False)
        if not self.multi_apis:
            self.multi_apis = [self.single_api.copy()]
            
        self.api_test_status = [0] * max(len(self.multi_apis), 1)

        self.init_ui()
        
        # 根据模式初始化界面读取的数据源 (-1 代表单模式)
        if self.is_multi_mode:
            self.load_slot_to_form(self.current_api_index)
        else:
            self.load_slot_to_form(-1)

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
        self.form_frame.pack(side="left", fill="both", expand=True, padx=(0, 5)) 

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

        # 🌟 API 启用开关（样式同网络代理）：关闭时该 API 不参与并发分析
        #    说明文字颜色随状态变化：启用=蓝（与"选择服务商"下拉框一致 #3B8ED0）、关闭=红
        self.enable_switch = ctk.CTkSwitch(tab_frame, text="当前API已启用", font=("Microsoft YaHei", 14, "bold"),
                                           text_color="#3B8ED0", command=self.toggle_api_enable)
        self.enable_switch.pack(side="left", padx=(15, 0))

        params_box = ctk.CTkFrame(self.form_frame, fg_color="transparent")
        params_box.pack(fill="x", pady=5)
        
        ctk.CTkLabel(params_box, text="模型URL", font=("Microsoft YaHei", 14)).grid(row=0, column=0, padx=10, pady=10, sticky="e")
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

        # 🌟 禁用思考开关：qwen 等推理模型勾选后直接输出 content（更快、避免答案进 reasoning_content）
        ctk.CTkLabel(params_box, text="推理模式", font=("Microsoft YaHei", 14)).grid(row=3, column=0, padx=10, pady=10, sticky="e")
        self.disable_thinking_check = ctk.CTkCheckBox(
            params_box, text="禁用思考（推理模型可选，勾选后直接输出、更快）",
            font=("Microsoft YaHei", 14), border_color="#008CBA", hover_color="#008CBA")
        self.disable_thinking_check.grid(row=3, column=1, pady=10, sticky="w")

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
        if index == -1: # 单模式状态
            status = self.single_test_status
            is_selected = True
        else: # 多模式状态
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

        border_width = 4 if is_selected else 1   # 🌟 选中态蓝边框（原样式 +40%）
        border_color = "#008CBA" if is_selected else "#A0A0A0"

        return bg_color, text_color, border_width, border_color

    def _create_api_square(self, master, index, bg, tc, bw, bc, disabled=False, command=None):
        """原生 CTkButton 圆角方形 API 块（与"改之前的样式"一致的 CustomTkinter 抗锯齿渲染）。

        圆角 12：外沿大圆角，选中态（bw=4）时内沿自动收窄到 8，即用户认可的外12内8；
        选中态蓝色加粗边框；禁用（API 关闭）时叠加红色 ✕（内缩不超出圆角边界，
        中央数字由 CTkButton 自身 label 绘制，不被遮挡）。"""
        return ApiSquareButton(
            master, text=str(index + 1), width=30, height=30,
            corner_radius=12, border_width=bw, border_color=bc,
            fg_color=bg, text_color=tc, hover_color=bg,
            font=("Microsoft YaHei", 14, "bold"),
            command=command, disabled=disabled,
        )

    def render_door_panel(self):
        for widget in self.right_panel.winfo_children():
            widget.destroy()

        if not self.is_multi_mode:
            self.btn_test_all.pack_forget()

            slot_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
            slot_frame.pack(side="left", fill="both", expand=True, padx=5, pady=10)
            
            # 单模式渲染专属外观（禁用时叠加 ✕）
            bg, tc, bw, bc = self.get_slot_appearance(-1)
            btn_1 = self._create_api_square(slot_frame, 0, bg, tc, bw, bc,
                                            disabled=not self.single_api.get('enabled', True))
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
                # 🌟 Canvas 方形块：禁用时叠加红色 ✕（两根细斜线，不挡中央数字）
                sq = self._create_api_square(grid_frame, i, bg, tc, bw, bc,
                                             disabled=not self.multi_apis[i].get('enabled', True),
                                             command=lambda idx=i: self.switch_api_slot(idx))
                sq.grid(row=row, column=col, padx=4, pady=4)
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
            self.load_slot_to_form(-1)
        else:
            self.load_slot_to_form(self.current_api_index)

    def add_api_slot(self):
        self.save_current_slot_to_memory()
        
        default_prov = self.config.get('ai_provider', 'Google Gemini')
        tpl = self.config.get('providers', {}).get(default_prov, {})
        new_api = {
            'provider': default_prov,
            'url': tpl.get('url', ''),
            'model': tpl.get('model', ''),
            'api_key': '',
            'enabled': True,  # 🌟 新节点默认启用
            'disable_thinking': False  # 🌟 新节点默认不禁用思考
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
        data = {
            'provider': self.provider_var.get(),
            'url': self.url_entry.get().strip(),
            'model': self.name_entry.get().strip(),
            'api_key': self.real_api_key,
            'enabled': bool(self.enable_switch.get()),  # 🌟 API 启用/关闭
            'disable_thinking': bool(self.disable_thinking_check.get())  # 🌟 禁用思考
        }
        if not self.is_multi_mode:
            self.single_api = data
        else:
            self.multi_apis[self.current_api_index] = data

    def toggle_api_enable(self):
        """切换当前 API 槽位的启用/关闭状态（开关样式同网络代理）。"""
        self.save_current_slot_to_memory()
        self._refresh_enable_switch()
        self.render_door_panel()

    def _refresh_enable_switch(self):
        """按开关当前状态刷新说明文字与颜色：启用=蓝（与下拉框一致 #3B8ED0）、关闭=红。"""
        enabled = bool(self.enable_switch.get())
        self.enable_switch.configure(
            text="当前API已启用" if enabled else "当前API已关闭",
            text_color="#3B8ED0" if enabled else "#F44336",
        )

    def load_slot_to_form(self, index):
        if index == -1 or not self.is_multi_mode:
            data = self.single_api
        else:
            self.current_api_index = index
            data = self.multi_apis[index]
            
        self.provider_var.set(data.get('provider', 'Google Gemini'))
        self.url_entry.delete(0, 'end'); self.url_entry.insert(0, data.get('url', ''))
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, data.get('model', ''))
        self.real_api_key = data.get('api_key', '')

        self.is_key_visible = False
        self.btn_eye.configure(text="🔒")
        # 🌟 始终以隐藏密码模式展示（show=●）：输入框内直接放真实 key，由掩码显示成圆点，
        #    不再用占位圆点 + 无掩码的 hack（旧逻辑导致粘贴的 key 无法自动保存）。
        self.key_entry.configure(show="●")
        self.key_entry.delete(0, 'end')
        self.key_entry.insert(0, self.real_api_key)

        # 🌟 同步 API 启用开关状态
        enabled = data.get('enabled', True)
        if enabled:
            self.enable_switch.select()
        else:
            self.enable_switch.deselect()
        self._refresh_enable_switch()

        # 🌟 同步禁用思考状态
        if data.get('disable_thinking', False):
            self.disable_thinking_check.select()
        else:
            self.disable_thinking_check.deselect()

        self.render_door_panel()

    def on_provider_change(self, new_provider):
        tpl = self.config.get('providers', {}).get(new_provider, {})
        self.url_entry.delete(0, 'end'); self.url_entry.insert(0, tpl.get('url', ''))
        self.name_entry.delete(0, 'end'); self.name_entry.insert(0, tpl.get('model', ''))

    def run_single_test(self):
        self.save_current_slot_to_memory()
        self.btn_test_single.configure(state="disabled", text="测试中...")
        
        if self.is_multi_mode:
            api_data = self.multi_apis[self.current_api_index]
            idx = self.current_api_index
            lbl = f"API-{idx + 1}"
        else:
            api_data = self.single_api
            idx = -1
            lbl = "单模式 API"
            
        self.lbl_test_result.configure(text=f"正在检测 {lbl}...", text_color="black")

        threading.Thread(target=self._perform_single_test, args=(api_data, idx), daemon=True).start()

    def run_multi_test(self):
        self.save_current_slot_to_memory()
        self.lbl_test_result.configure(text="正在检测所有接口...", text_color="black")

        threading.Thread(target=self._perform_batch_test, daemon=True).start()

    def _proxy_config(self):
        """把表单代理状态转成 llm_client.build_proxy 需要的 config 子集（不再写 os.environ）。"""
        return {
            'ai_use_proxy': bool(self.proxy_switch.get()),
            'ai_proxy_server': self.proxy_server_entry.get(),
            'ai_proxy_port': self.proxy_port_entry.get(),
        }

    def _test_core_logic(self, api):
        if not api.get('api_key', '').strip():
            return False, "未填写 API Key"

        try:
            # 🌟 复用与 pipelines 完全一致的 LLM 调用（单一事实来源，消除两套逻辑漂移）。
            #    测试提示词极简，防止推理模型过度思考延迟。
            proxies, proxy_url = build_proxy(self._proxy_config())
            result_text, _ = call_llm(
                api, build_connect_test_prompt(), "test",
                proxies=proxies, proxy_url=proxy_url,
            )
            if result_text and result_text.strip():
                return True, "OK"
            return False, "返回为空"
        except Exception as e:
            return False, str(e)[:30]

    def _perform_single_test(self, api_data, index):
        success, msg = self._test_core_logic(api_data)

        if index == -1:
            self.single_test_status = 1 if success else -1
            name_lbl = "单模式 API"
        else:
            self.api_test_status[index] = 1 if success else -1
            name_lbl = f"API-{index+1}"

        self.after(0, self.render_door_panel)
        if success:
            self.after(0, self._show_result, True, f"✅ {name_lbl} 测试通过！")
        else:
            self.after(0, self._show_result, False, f"❌ {name_lbl} 失败: {msg}")

    def _perform_batch_test(self):
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
        
        p_name = self.single_api['provider']
        self.config['ai_provider'] = p_name
        
        if p_name not in self.config['providers']:
            self.config['providers'][p_name] = {}
            
        self.config['providers'][p_name]['url'] = self.single_api['url']
        self.config['providers'][p_name]['model'] = self.single_api['model']
        self.config['providers'][p_name]['api_key'] = self.single_api['api_key']
        self.config['single_api_enabled'] = bool(self.single_api.get('enabled', True))  # 🌟 单模式启用状态持久化
        self.config['single_api_disable_thinking'] = bool(self.single_api.get('disable_thinking', False))  # 🌟 单模式禁用思考持久化
        
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
        # 🌟 直接读取输入框当前内容（掩码模式下 get() 仍返回真实 key），保证自动保存。
        # 注：不能用 focus_get()==self.key_entry 判断——CTkEntry 内部封装的是 tk.Entry，
        #     focus_get() 返回内部 entry，与 self.key_entry 恒不等，旧逻辑导致永远不同步。
        self.real_api_key = self.key_entry.get().strip()

    def on_key_focus_in(self, event):
        pass  # 输入框默认已是隐藏密码模式，无需在获得焦点时切换

    def on_key_focus_out(self, event):
        self._sync_real_key_from_entry()

    def toggle_key_visibility(self):
        self._sync_real_key_from_entry()
        self.is_key_visible = not self.is_key_visible
        self.btn_eye.configure(text="👁" if self.is_key_visible else "🔒")
        self.key_entry.configure(show="" if self.is_key_visible else "●")

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