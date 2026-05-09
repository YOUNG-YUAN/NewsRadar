import os
import sys
import subprocess
from .config_mgr import BASE_DIR

try:
    import markdown
    HAS_MARKDOWN = True
except ImportError: 
    HAS_MARKDOWN = False
    
def get_res_path(rel_path):
    """
    专门为打包设计的路径获取函数
    rel_path: 资源文件的名称，如 'icon.svg'
    """
    # 如果是打包环境，资源在 sys._MEIPASS 下
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, rel_path)

# 使用时：
class ReportExporter:
    def __init__(self, log_callback):
        self.log_callback = log_callback
        # 🌟 无论在谁的电脑上，这里都能拿到正确的 icon 绝对路径
        self.icon_svg_path = get_res_path("icon.svg")

def normalize_category(raw_cat):
    c = str(raw_cat).lower()
    if "中国" in c or "china" in c: return "中国 China"
    if "美国" in c or "u.s" in c or "usa" in c or "america" in c: return "美国 US"
    if "亚洲" in c or "asia" in c: return "亚洲 Asia"
    if "欧洲" in c or "europe" in c or "russia" in c or "俄罗斯" in c: return "欧洲 Europe"
    if "ai" in c or "智能" in c or "robot" in c or "机器" in c: return "人工智能与机器人 AI and Robotics"
    if "科技" in c or "tech" in c: return "科技 Tech"
    if "商业" in c or "business" in c or "biz" in c: return "商业 Business"
    if "金融" in c or "市场" in c or "market" in c or "finance" in c: return "市场与金融 Markets and Finance"
    if "科学" in c or "science" in c: return "科学 Science"
    if "健康" in c or "health" in c or "医疗" in c or "medical" in c: return "健康 Health"
    if "能源" in c or "energy" in c: return "能源 Energy"
    if "环境" in c or "气候" in c or "climate" in c or "environment" in c: return "环境与气候 Environment and Climate"
    if "生活" in c or "lifestyle" in c or "life" in c: return "生活 Lifestyle"
    if "文艺" in c or "文化" in c or "art" in c or "culture" in c: return "文艺 Arts and Culture"
    if "体育" in c or "sport" in c: return "体育 Sports"
    return "世界 World"

ORDERED_CATEGORIES = [
    "中国 China", "美国 US", "亚洲 Asia", "欧洲 Europe", "世界 World",
    "商业 Business", "市场与金融 Markets and Finance", "人工智能与机器人 AI and Robotics",
    "科技 Tech", "科学 Science", "健康 Health", "能源 Energy",
    "环境与气候 Environment and Climate", "生活 Lifestyle", "文艺 Arts and Culture", "体育 Sports"
]

class ReportExporter:
    """独立的新闻简报渲染与导出引擎"""
    def __init__(self, log_callback):
        self.log_callback = log_callback

    def export_all(self, session_id, intercept_display, all_json_items, config):
        """主入口：依次生成 MD, HTML, PDF"""
        self.log_callback(f"📝 正在排版报告与分配字体引擎...")
        
        # 1. 生成并保存 Markdown
        md_text, base_name = self._merge_and_render_markdown(session_id, intercept_display, all_json_items, config)
        save_dir = config['save_path']
        
        with open(os.path.join(save_dir, base_name + ".md"), 'w', encoding='utf-8') as f: 
            f.write(md_text)
        
        if not HAS_MARKDOWN:
            self.log_callback(f"✅ 报告已生成 MD: {base_name}.md")
            return

        # 2. 生成并保存精美 HTML
        html_content = self._generate_html_with_fonts(md_text, config)
        html_abs = os.path.abspath(os.path.join(save_dir, base_name + ".html"))
        with open(html_abs, 'w', encoding='utf-8') as f: 
            f.write(html_content)
        
        # 3. 唤醒系统浏览器静默生成完美 PDF
        pdf_abs = os.path.abspath(os.path.join(save_dir, base_name + ".pdf"))
        if self._generate_pdf_with_browser(html_abs, pdf_abs):
            self.log_callback(f"✅ 全套报告已生成 (PDF + HTML + MD): {base_name}")
        else:
            self.log_callback(f"⚠️ 系统自动转PDF失败，已保留精美版 HTML: {base_name}.html")

    def _merge_and_render_markdown(self, session_id, intercept_display, all_json_items, config):
        categorized_data = {}
        for item in all_json_items:
            raw_cats = item.get("categories", ["世界 (World)"])
            standard_cats = list(set(normalize_category(c) for c in raw_cats))
            item["categories"] = standard_cats
            for cat in standard_cats:
                if cat not in categorized_data: 
                    categorized_data[cat] = []
                categorized_data[cat].append(item)
                
        provider = config.get('ai_provider', 'Google Gemini')
        model_name = config.get('providers', {}).get(provider, {}).get('model', 'Unknown')
        time_range_str = "全量回溯获取" if config.get('fetch_all', False) else f"近 {config.get('listen_freq', '60m')}"

        md_lines = [
            f"# 📡 全球新闻 AI 监听简报", 
            f"> 🧠 **生成模型**：{provider} | {model_name}", 
            f"> 🕒 **截获时间**：{intercept_display}", 
            f"> ⏱️ **监听范围**：{time_range_str}\n", 
            "## 📑 栏目导航"
        ]
        
        for cat in ORDERED_CATEGORIES:
            if cat in categorized_data: 
                safe_anchor = cat.replace(' ', '-').replace('&', 'and')
                md_lines.append(f"* [{cat}](#{safe_anchor})")
        md_lines.append("\n---\n")
        
        for cat in ORDERED_CATEGORIES:
            if cat not in categorized_data: 
                continue
            
            safe_anchor = cat.replace(' ', '-').replace('&', 'and')
            md_lines.append(f"## <a id=\"{safe_anchor}\"></a>{cat}")
            
            items = categorized_data[cat]
            items.sort(key=lambda x: (not x.get("is_priority", False), x.get("time", "")), reverse=True)
            
            for item in items:
                star, title_cn = ("⭐", item.get("translated_title", "未命名")) if item.get("is_priority", False) else ("📰", item.get("translated_title", "未命名"))
                kw_str = " ".join([f'<span class="keyword">**{k}**</span>' for k in item.get("keywords", [])])
                cat_str = ", ".join(item.get("categories", []))
                source_str = item.get("source", "未提供")
                time_str = item.get("time", "未提供")
                url_str = item.get("url", "#")
                
                md_lines.append(f"### [{star}] {title_cn}")
                md_lines.append(f"* **Title**: {item.get('original_title', 'No Title')}")
                md_lines.append(f"* **关键词**: {kw_str}")
                md_lines.append(f"* **情报**: **{item.get('summary', '')}**")
                md_lines.append(f"* <span class=\"metadata\">📎 **元数据**: 栏目 `[{cat_str}]` | 来源 {source_str} | 时间 {time_str} | [🔗 原文链接]({url_str})</span>\n")
                
        return "\n".join(md_lines), f"NewsSummary_{session_id}"

    def _generate_pdf_with_browser(self, html_path, pdf_path):
        browser_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        
        for exe in browser_paths:
            if os.path.exists(exe):
                try:
                    CREATE_NO_WINDOW = 0x08000000
                    cmd = [exe, '--headless', '--disable-gpu', f'--print-to-pdf={pdf_path}', '--no-pdf-header-footer', html_path]
                    subprocess.run(cmd, creationflags=CREATE_NO_WINDOW, check=True, timeout=30)
                    return True
                except Exception:
                    continue
        return False

    def _generate_html_with_fonts(self, md_text, config):
        if not HAS_MARKDOWN: 
            return ""
            
        html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
        fonts_dir = os.path.join(BASE_DIR, "fonts").replace("\\", "/")

        logo_html = ""
        icon_png = os.path.join(BASE_DIR, "icon.png").replace("\\", "/")
        icon_svg = os.path.join(BASE_DIR, "icon.svg").replace("\\", "/")
        if os.path.exists(icon_svg):
            logo_html = f'<img src="file:///{icon_svg}" class="report-logo">'
        elif os.path.exists(icon_png):
            logo_html = f'<img src="file:///{icon_png}" class="report-logo">'

        def get_font_css(name, file_name):
            if file_name and os.path.exists(os.path.join(BASE_DIR, "fonts", file_name)):
                font_url = f"file:///{fonts_dir}/{file_name}"
                return f"@font-face {{ font-family: '{name}'; src: url('{font_url}'); }}\n"
            return ""

        css_faces = ""
        css_faces += get_font_css('HeaderFont', config.get('font_header', ''))
        css_faces += get_font_css('ArticleFont', config.get('font_article', ''))
        css_faces += get_font_css('BodyFont', config.get('font_body', ''))
        css_faces += get_font_css('AccentFont', config.get('font_accent', ''))
        css_faces += get_font_css('KeyFont', config.get('font_keywords', ''))

        font_header_family = "'HeaderFont', 'Microsoft YaHei', sans-serif" if config.get('font_header') else "'Microsoft YaHei', sans-serif"
        font_article_family = "'ArticleFont', 'Microsoft YaHei', sans-serif" if config.get('font_article') else "'Microsoft YaHei', sans-serif"
        font_body_family = "'BodyFont', 'SimSun', serif" if config.get('font_body') else "'SimSun', serif"
        font_accent_family = "'AccentFont', Consolas, monospace" if config.get('font_accent') else "Consolas, monospace"
        font_key_family = "'KeyFont', 'Microsoft YaHei', sans-serif" if config.get('font_keywords') else "'Microsoft YaHei', sans-serif"

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            {css_faces}
            body {{ position: relative; font-family: {font_body_family}; line-height: 1.6; padding: 30px; background-color: #FAFAFA; max-width: 950px; margin: 0 auto; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
            .report-logo {{ position: absolute; top: 40px; right: 40px; width: 75px; height: auto; z-index: 100; opacity: 0.85; }}
            h1, h2 {{ font-family: {font_header_family}; color: #2C3E50; border-bottom: 2px solid #E0E0E0; padding-bottom: 8px; margin-top: 30px; }}
            h3 {{ font-family: {font_article_family}; color: #34495E; margin-top: 25px; }}
            code {{ font-family: {font_accent_family}; background: #E8ECEF; padding: 3px 6px; border-radius: 4px; font-size: 0.9em; border: 1px solid #D5DBDB; }}
            .metadata {{ font-family: {font_accent_family}; font-size: 0.9em; color: #7F8C8D; }}
            .keyword {{ font-family: {font_key_family}; color: #D32F2F; font-weight: bold; margin-right: 5px; }}
            a {{ color: #2980B9; text-decoration: none; border-bottom: 1px dotted #2980B9; }}
            a:hover {{ border-bottom: 1px solid #2980B9; background-color: #EAF2F8; }}
            blockquote {{ border-left: 4px solid #3498DB; margin: 15px 0; padding: 10px 15px; color: #555; background: #EBF5FB; border-radius: 0 4px 4px 0; font-family: {font_body_family}; }}
        </style>
        </head>
        <body>
        {logo_html}
        {html_body}
        </body>
        </html>
        """
        return html_template