import os
import json
import time
import requests
import feedparser
import threading
import concurrent.futures
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import google.generativeai as genai
from openai import OpenAI
from dateutil import parser as date_parser
from .config_mgr import ConfigManager, RAW_DIR, FAILED_DIR

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

class FetcherThread(threading.Thread):
    def __init__(self, log_callback):
        super().__init__()
        self.log_callback = log_callback
        self.is_running = True
        self.is_paused = False 
        self.daemon = True 

    def get_sleep_seconds(self, freq_str):
        try:
            unit = freq_str[-1].lower()
            val = int(freq_str[:-1])
            if unit == 'm': return val * 60
            elif unit == 'h': return val * 3600
            elif unit == 'd': return val * 86400
        except: return 3600
        return 3600

    def run(self):
        self.log_callback("流水线1 (数据获取) 已启动...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
                
            config = ConfigManager.load_config()
            sources = ConfigManager.load_sources()
            history = set(ConfigManager.load_history())
            
            sleep_secs = self.get_sleep_seconds(config.get('listen_freq', '60m'))
            end_time_utc = datetime.now(timezone.utc)
            start_time_utc = end_time_utc - timedelta(seconds=sleep_secs)
            
            intercept_time_obj = datetime.now()
            session_timestamp = intercept_time_obj.strftime("%Y-%m-%d-%H%M") 
            intercept_display = intercept_time_obj.strftime("%Y-%m-%d %H:%M")  
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            # 🌟 关键修复：使用正确的键名 rss_use_proxy，并确协议头格式
            if config.get('rss_use_proxy', False):
                proxy_srv = config.get('rss_proxy_server', 'http://127.0.0.1')
                if not proxy_srv.startswith('http'):
                    proxy_srv = 'http://' + proxy_srv
                proxy_url = f"{proxy_srv}:{config.get('rss_proxy_port', '10808')}"
                rss_proxies = {'http': proxy_url, 'https': proxy_url}
            else:
                rss_proxies = None
            
            all_new_items_this_session = []
            is_fetch_all = config.get('fetch_all', False) 

            for src in sources:
                if not self.is_running: break
                if self.is_paused: break 
                if not src.get('checked', False): continue
                
                self.log_callback(f"正在获取: {src['name']}...")
                
                feed_data = None
                for attempt in range(1, 4):
                    if not self.is_running or self.is_paused: break
                    try:
                        # 🌟 使用修复后的代理字典
                        res = requests.get(src['url'], headers=headers, proxies=rss_proxies, timeout=15)
                        res.raise_for_status()
                        
                        temp_feed = feedparser.parse(res.content)
                        if temp_feed.bozo and not temp_feed.entries:
                            raise ValueError(f"解析失败或被拦截 (Bozo={temp_feed.bozo})")
                            
                        feed_data = temp_feed
                        break 
                        
                    except Exception as e:
                        if attempt < 3:
                            self.log_callback(f"⚠️ 获取 {src['name']} 失败 (尝试 {attempt}/3)，等待 2 秒重试...")
                            time.sleep(2)
                        else:
                            err_msg = str(e).split('\n')[0][:40]
                            self.log_callback(f"❌ 获取 {src['name']} 彻底失败: {err_msg}...")

                if not feed_data: continue

                for entry in feed_data.entries:
                    link = entry.link
                    if link not in history:
                        is_valid_time = is_fetch_all
                        if not is_valid_time:
                            try:
                                pub_time = date_parser.parse(entry.published)
                                if start_time_utc <= pub_time <= end_time_utc:
                                    is_valid_time = True
                            except Exception: pass 
                                
                        if is_valid_time:
                            desc = BeautifulSoup(entry.description, "html.parser").get_text() if hasattr(entry, 'description') else ""
                            try: display_time = date_parser.parse(entry.published).strftime("%Y-%m-%d %H:%M")
                            except: display_time = intercept_display

                            all_new_items_this_session.append({
                                "source": src['name'], "title": entry.title,
                                "description": desc[:300], "url": link, "time": display_time
                            })
                            ConfigManager.add_to_history(link)
                            history.add(link)

            if not self.is_paused:
                if all_new_items_this_session:
                    try:
                        chunk_size = int(config.get('batch_size', '30'))
                        if chunk_size <= 0: chunk_size = 30
                    except: chunk_size = 30
                        
                    for idx, i in enumerate(range(0, len(all_new_items_this_session), chunk_size)):
                        chunk_items = all_new_items_this_session[i:i + chunk_size]
                        batch_data = {"session_timestamp": session_timestamp, "intercept_display": intercept_display, "news_list": chunk_items}
                        batch_file = os.path.join(RAW_DIR, f"temp_RSS_batch_{session_timestamp}_{idx}.json")
                        with open(batch_file, 'w', encoding='utf-8') as f:
                            json.dump(batch_data, f, ensure_ascii=False)
                    self.log_callback(f"获取完成！{len(all_new_items_this_session)} 条资讯已分拆送入AI队列。")
                else:
                    self.log_callback("当前周期无新资讯更新。")

            for _ in range(sleep_secs):
                if not self.is_running: break
                while self.is_paused and self.is_running: time.sleep(1) 
                time.sleep(1)

    def stop(self): self.is_running = False

class AnalyzerThread(threading.Thread):
    def __init__(self, log_callback, token_callback):
        super().__init__()
        self.log_callback = log_callback
        self.token_callback = token_callback
        self.is_running = True
        self.is_paused = False
        self.daemon = True
        self.token_lock = threading.Lock()

    def _process_single_chunk(self, chunk_file, config):
        if not self.is_running or self.is_paused: return None, None
        
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                session_timestamp = batch_data["session_timestamp"]
                intercept_display = batch_data["intercept_display"]
                current_chunk = batch_data["news_list"]
        except Exception as e:
            self.log_callback(f"读取临时文件失败: {e}")
            os.remove(chunk_file)
            return None, None

        self.log_callback(f"🚀 启动分析: {os.path.basename(chunk_file)}")
        text_data = "".join([f"[{i+1}] 标题:{n['title']}\n来源:{n['source']} | 时间: {n['time']}\n简介:{n['description']}\n链接:{n['url']}\n\n" for i, n in enumerate(current_chunk)])

        user_prompt = config.get("user_prompt", "").strip()
        interest_focus = f"重点关注以下领域：{user_prompt}" if user_prompt else "重点关注：AI大模型、地缘政治、科技巨头商业动态"

        prompt = f"""
        你是一位情报分析师。分析这批外媒新闻。
        【关注焦点】(判定 is_priority 为 true 的标准)：{interest_focus}
        【可选的栏目大类 (必须且只能使用以下名称)】：
        中国 (China) | 美国 (U.S.) | 亚洲 (Asia) | 欧洲 (Europe) | 世界 (World) | 商业 (Business) | 市场与金融 (Markets & Finance) | 人工智能与机器人 (AI & Robotics) | 科技 (Tech) | 科学 (Science) | 健康 (Health) | 能源 (Energy) | 环境与气候 (Environment & Climate) | 生活 (Lifestyle) | 文艺 (Arts & Culture) | 体育 (Sports)
        
        必须以严格的 JSON 数组格式返回结果。
        示例: [{{"is_priority": true, "translated_title": "...", "original_title": "...", "keywords": ["..."], "summary": "...", "categories": ["..."], "source": "...", "time": "...", "url": "..."}}]
        """

        for attempt in range(1, 4):
            if not self.is_running or self.is_paused: return None, None
            try:
                provider = config.get('ai_provider', 'Google Gemini')
                provider_cfg = config.get('providers', {}).get(provider, {})
                url, model_name, api_key = provider_cfg.get('url', ''), provider_cfg.get('model', ''), provider_cfg.get('api_key', '')

                # 🌟 AI 代理逻辑保持正确 (使用 ai_use_proxy)
                if config.get('ai_use_proxy', False):
                    proxy_srv = config.get('ai_proxy_server', 'http://127.0.0.1')
                    if not proxy_srv.startswith('http'): proxy_srv = 'http://' + proxy_srv
                    proxy_url = f"{proxy_srv}:{config.get('ai_proxy_port', '10808')}"
                    os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_url, proxy_url
                else:
                    os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)

                if provider == "Google Gemini":
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_name, system_instruction=prompt)
                    resp = model.generate_content(text_data)
                    result_text = resp.text
                    tokens_used = int((len(text_data) + len(result_text)) * 0.8)
                elif provider == "Claude":
                    headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
                    data = {"model": model_name, "max_tokens": 4096, "system": prompt, "messages": [{"role": "user", "content": text_data}], "temperature": 0.1}
                    resp = requests.post(url, headers=headers, json=data, proxies=None if not os.environ.get('HTTP_PROXY') else {'http': os.environ['HTTP_PROXY'], 'https': os.environ['HTTPS_PROXY']})
                    resp.raise_for_status()
                    resp_json = resp.json()
                    result_text = resp_json['content'][0]['text']
                    tokens_used = resp_json.get('usage', {}).get('input_tokens', 0) + resp_json.get('usage', {}).get('output_tokens', 0)
                else:
                    client = OpenAI(api_key=api_key, base_url=url)
                    resp = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text_data}], temperature=0.1)
                    result_text = resp.choices[0].message.content
                    tokens_used = resp.usage.total_tokens if resp.usage else int((len(text_data) + len(result_text)) * 0.8)

                with self.token_lock:
                    config['total_tokens'] += tokens_used
                    ConfigManager.save_config(config)
                    self.token_callback(config['total_tokens'])
                
                clean_json_str = result_text.replace("```json", "").replace("```", "").strip()
                match = re.search(r'\[\s*\{.*?\}\s*\]', clean_json_str, re.DOTALL)
                
                if match:
                    parsed_items = json.loads(match.group(0))
                    self.log_callback(f"✅ {os.path.basename(chunk_file)} 成功解析 {len(parsed_items)} 条情报！")
                    os.remove(chunk_file)
                    return session_timestamp, {"intercept_display": intercept_display, "items": parsed_items}
                else: raise ValueError("JSON 解析失败。")

            except Exception as e:
                if attempt < 3:
                    self.log_callback(f"⚠️ {os.path.basename(chunk_file)} 分析失败 (尝试 {attempt}/3)...")
                    time.sleep(2)
                else:
                    self.log_callback(f"❌ {os.path.basename(chunk_file)} 彻底失败: {str(e)[:50]}")
                    try: os.rename(chunk_file, os.path.join(FAILED_DIR, os.path.basename(chunk_file)))
                    except: pass
                    return None, None

    def _merge_and_render_markdown(self, session_id, intercept_display, all_json_items, config):
        self.log_callback(f"📝 正在整合报告...")
        categorized_data = {}
        for item in all_json_items:
            raw_cats = item.get("categories", ["世界 (World)"])
            standard_cats = list(set(normalize_category(c) for c in raw_cats))
            item["categories"] = standard_cats
            for cat in standard_cats:
                if cat not in categorized_data: categorized_data[cat] = []
                categorized_data[cat].append(item)
                
        provider = config.get('ai_provider', 'Google Gemini')
        model_name = config.get('providers', {}).get(provider, {}).get('model', 'Unknown')
        time_range_str = "全量回溯获取" if config.get('fetch_all', False) else f"近 {config.get('listen_freq', '60m')}"

        md_lines = [f"# 📡 全球新闻 AI 监听简报", f"> 🧠 **生成模型**：{provider} | {model_name}", f"> 🕒 **截获时间**：{intercept_display}", f"> ⏱️ **监听范围**：{time_range_str}\n", "## 📑 栏目导航"]
        for cat in ORDERED_CATEGORIES:
            if cat in categorized_data: md_lines.append(f"* [{cat}](#{cat.lower().replace(' ', '-')})")
        md_lines.append("\n---\n")
        
        for cat in ORDERED_CATEGORIES:
            if cat not in categorized_data: continue
            md_lines.append(f"## {cat}")
            items = categorized_data[cat]
            items.sort(key=lambda x: (not x.get("is_priority", False), x.get("time", "")), reverse=True)
            for item in items:
                star, title_cn = ("⭐", item.get("translated_title", "未命名")) if item.get("is_priority", False) else ("📰", item.get("translated_title", "未命名"))
                kw_str = " ".join([f'<font color="#E53935">**{k}**</font>' for k in item.get("keywords", [])])
                md_lines.append(f"### [{star}] {title_cn}\n* **Title**: {item.get('original_title', 'No Title')}\n* **关键词**: {kw_str}\n* **情报**: **{item.get('summary', '')}**\n* 📎 **元数据**: 来源 {item.get('source', 'Unknown')} | [🔗 原文链接]({item.get('url', '#')})\n")
        return "\n".join(md_lines), f"NewsSummary_{session_id}.md"

    def run(self):
        self.log_callback("流水线2 (AI分析) 已启动...")
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
            raw_files = [f for f in os.listdir(RAW_DIR) if f.startswith('temp_RSS_batch_') and f.endswith('.json')]
            if not raw_files:
                time.sleep(2)
                continue

            config = ConfigManager.load_config()
            sessions_dict = {}
            for f_name in raw_files:
                sid = f_name.split('_')[3]; sessions_dict.setdefault(sid, []).append(os.path.join(RAW_DIR, f_name))

            current_session = sorted(sessions_dict.keys())[0]
            all_json_items, intercept_display = [], ""
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(self._process_single_chunk, fp, config): fp for fp in sessions_dict[current_session]}
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res[1]: intercept_display, all_json_items = res[1]["intercept_display"], all_json_items + res[1]["items"]

            if all_json_items:
                md, name = self._merge_and_render_markdown(current_session, intercept_display, all_json_items, config)
                with open(os.path.join(config['save_path'], name), 'w', encoding='utf-8') as f: f.write(md)
                self.log_callback(f"✅ 报告已生成: {name}")
    def stop(self): self.is_running = False