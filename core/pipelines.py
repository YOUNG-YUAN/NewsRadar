import os
import json
import time
import requests
import feedparser
import threading
import concurrent.futures
import queue
import re
import uuid
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from openai import OpenAI
from dateutil import parser as date_parser

from .config_mgr import ConfigManager, RAW_DIR, FAILED_DIR, DB_DIR
from .exporter import ReportExporter

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
        self.log_callback("流水线1 (多维数据截获) 已启动...")
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
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            if config.get('rss_use_proxy', False):
                proxy_srv = config.get('rss_proxy_server', 'http://127.0.0.1')
                if not proxy_srv.startswith('http'): proxy_srv = 'http://' + proxy_srv
                proxy_url = f"{proxy_srv}:{config.get('rss_proxy_port', '10808')}"
                rss_proxies = {'http': proxy_url, 'https': proxy_url}
            else: 
                rss_proxies = None
            
            date_groups = {} 
            is_fetch_all = config.get('fetch_all', False) 
            fetched_count = 0

            for src in sources:
                if not self.is_running or self.is_paused: break
                if not src.get('checked', False): continue
                
                self.log_callback(f"正在获取: {src['name']}...")
                feed_data = None
                for attempt in range(1, 4):
                    if not self.is_running or self.is_paused: break
                    try:
                        res = requests.get(src['url'], headers=headers, proxies=rss_proxies, timeout=15)
                        res.raise_for_status()
                        temp_feed = feedparser.parse(res.content)
                        if temp_feed.bozo and not temp_feed.entries: raise ValueError(f"解析失败 (Bozo)")
                        feed_data = temp_feed
                        break 
                    except Exception as e:
                        if attempt < 3:
                            self.log_callback(f"⚠️ 获取 {src['name']} 失败 (尝试 {attempt}/3)...")
                            time.sleep(2)
                        else:
                            self.log_callback(f"❌ 获取 {src['name']} 彻底失败: {str(e).splitlines()[0][:40]}")

                if not feed_data: continue
                    
                for entry in feed_data.entries:
                    link = entry.link
                    if link not in history:
                        is_valid_time = is_fetch_all
                        pub_time = None
                        if not is_valid_time:
                            try:
                                pub_time = date_parser.parse(entry.published)
                                if start_time_utc <= pub_time <= end_time_utc: is_valid_time = True
                            except: pass 
                                
                        if is_valid_time:
                            desc = BeautifulSoup(entry.description, "html.parser").get_text() if hasattr(entry, 'description') else ""
                            try:
                                if not pub_time: pub_time = date_parser.parse(entry.published)
                                display_time = pub_time.strftime("%Y-%m-%d %H:%M")
                                date_str = pub_time.strftime("%Y-%m-%d")
                            except:
                                dt_now = datetime.now()
                                display_time = dt_now.strftime("%Y-%m-%d %H:%M")
                                date_str = dt_now.strftime("%Y-%m-%d")

                            date_groups.setdefault(date_str, []).append({
                                "source": src['name'], 
                                "title": entry.title,
                                "description": desc[:300], 
                                "url": link, 
                                "time": display_time
                            })
                            ConfigManager.add_to_history(link)
                            history.add(link)
                            fetched_count += 1

            if not self.is_paused:
                if fetched_count > 0:
                    for d_str, items in date_groups.items():
                        batch_file = os.path.join(RAW_DIR, f"raw_{d_str}_{uuid.uuid4().hex[:8]}.json")
                        with open(batch_file, 'w', encoding='utf-8') as f:
                            json.dump({"date": d_str, "news": items}, f, ensure_ascii=False)
                    self.log_callback(f"获取完成！共 {fetched_count} 条资讯已按日期分拆送入AI队列。")
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

    def _process_chunk(self, chunk_items, config, key_queue, session_tokens):
        if not self.is_running or self.is_paused: return None
        
        api_name, api_config = key_queue.get()
        self.log_callback(f"🚀 [{api_name}] 接单分析...")

        text_data = ""
        for i, n in enumerate(chunk_items):
            text_data += f"[{i+1}] 标题:{n['title']}\n来源:{n['source']} | 时间:{n['time']}\n简介:{n['description']}\n链接:{n['url']}\n\n"

        user_prompt = config.get("user_prompt", "").strip()
        interest_focus = f"重点关注以下领域：{user_prompt}" if user_prompt else "重点关注：AI大模型、地缘政治、科技巨头商业动态"
        output_lang = config.get("language", "zh")
        lang_instruction = "必须使用 简体中文 (Simplified Chinese) 输出摘要和翻译标题。" if output_lang == "zh" else "You MUST output the summary and translated_title in English."

        prompt = f"""你是一位情报分析师。分析这批外媒新闻。
        【关注焦点】(判定 is_priority 为 true 的标准)：{interest_focus}
        【可选的栏目大类 (必须且只能使用以下名称)】：
        中国 (China) | 美国 (U.S.) | 亚洲 (Asia) | 欧洲 (Europe) | 世界 (World) | 商业 (Business) | 市场与金融 (Markets & Finance) | 人工智能与机器人 (AI & Robotics) | 科技 (Tech) | 科学 (Science) | 健康 (Health) | 能源 (Energy) | 环境与气候 (Environment & Climate) | 生活 (Lifestyle) | 文艺 (Arts & Culture) | 体育 (Sports)
        【严格纪律】：
        1. 必须完全照抄我提供的 source, time 和 url，不可修改为“未提供”。
        2. {lang_instruction}
        必须以严格的 JSON 数组格式返回结果。
        示例: [{{"is_priority": true, "translated_title": "...", "original_title": "...", "keywords": ["..."], "summary": "...", "categories": ["..."], "source": "原样提取的来源", "time": "原样提取的时间", "url": "原样提取的链接"}}]
        """

        for attempt in range(1, 4):
            if not self.is_running or self.is_paused: 
                key_queue.put((api_name, api_config)); key_queue.task_done()
                return None
            try:
                provider = api_config.get('provider', 'Google Gemini')
                url = api_config.get('url', '')
                model_name = api_config.get('model', '')
                current_api_key = api_config.get('api_key', '')

                proxies = None
                if config.get('ai_use_proxy', False):
                    proxy_srv = config.get('ai_proxy_server', 'http://127.0.0.1')
                    if not proxy_srv.startswith('http'): proxy_srv = 'http://' + proxy_srv
                    proxy_url = f"{proxy_srv}:{config.get('ai_proxy_port', '10808')}"
                    proxies = {'http': proxy_url, 'https': proxy_url}
                    os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_url, proxy_url
                else:
                    os.environ.pop('HTTP_PROXY', None); os.environ.pop('HTTPS_PROXY', None)

                if provider == "Google Gemini":
                    headers = {"Content-Type": "application/json"}
                    data = {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": [{"parts": [{"text": text_data}]}]}
                    base = url.strip().rstrip('/')
                    if not base.endswith('models'): base = f"{base}/models"
                    full_url = f"{base}/{model_name}:generateContent?key={current_api_key}"
                    resp = requests.post(full_url, headers=headers, json=data, proxies=proxies, timeout=120)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    result_text = resp_json['candidates'][0]['content']['parts'][0]['text']
                    tokens_used = resp_json.get('usageMetadata', {}).get('totalTokenCount', int((len(text_data) + len(result_text)) * 0.8))
                else:
                    client = OpenAI(api_key=current_api_key, base_url=url)
                    resp = client.chat.completions.create(model=model_name, messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text_data}], temperature=0.1)
                    result_text = resp.choices[0].message.content
                    tokens_used = resp.usage.total_tokens if resp.usage else int((len(text_data) + len(result_text)) * 0.8)

                with self.token_lock:
                    session_tokens[api_name] = session_tokens.get(api_name, 0) + tokens_used
                    config['total_tokens'] += tokens_used
                    ConfigManager.save_config(config)
                    self.token_callback(config['total_tokens'])
                
                clean_json_str = result_text.replace("```json", "").replace("```", "").strip()
                match = re.search(r'\[\s*\{.*?\}\s*\]', clean_json_str, re.DOTALL)
                if match:
                    parsed_items = json.loads(match.group(0))
                    key_queue.put((api_name, api_config)); key_queue.task_done()
                    return parsed_items
                else: raise ValueError("JSON 解析失败。")
            except Exception as e:
                if attempt < 3: time.sleep(2)
                else:
                    self.log_callback(f"❌ [{api_name}] 彻底失败: {str(e)[:50]}")
                    key_queue.put((api_name, api_config)); key_queue.task_done()
                    return None

    def run(self):
        self.log_callback("流水线2 (增量情报分析) 已启动...")
        exporter = ReportExporter(self.log_callback)
        
        while self.is_running:
            if self.is_paused:
                time.sleep(1); continue
                
            raw_files = [f for f in os.listdir(RAW_DIR) if f.startswith('raw_') and f.endswith('.json')]
            if not raw_files:
                self._check_periodic_reports(exporter, ConfigManager.load_config())
                time.sleep(3); continue

            config = ConfigManager.load_config()
            target_file = os.path.join(RAW_DIR, sorted(raw_files)[0])
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    batch_data = json.load(f)
                date_str = batch_data['date']
                news_items = batch_data['news']
            except Exception:
                try: os.remove(target_file)
                except: pass
                continue

            active_apis = config.get('multi_apis', [])
            if not config.get('is_multi_mode', False) or not active_apis:
                fp = config.get('ai_provider', 'Google Gemini')
                active_apis = [{'provider': fp, 'url': config.get('providers', {}).get(fp, {}).get('url', ''), 'model': config.get('providers', {}).get(fp, {}).get('model', ''), 'api_key': config.get('providers', {}).get(fp, {}).get('api_key', '')}]

            valid_apis = [api for api in active_apis if api.get('api_key', '').strip()]
            if not valid_apis:
                self.log_callback("❌ 错误：未配置有效的 API Key，无法进行 AI 分析。")
                time.sleep(5); continue
                
            key_queue = queue.Queue()
            for idx, api in enumerate(valid_apis): key_queue.put((f"API-{idx+1}", api))
            
            try: chunk_size = int(config.get('batch_size', '30'))
            except: chunk_size = 30
            if chunk_size <= 0: chunk_size = 30

            chunks = [news_items[i:i + chunk_size] for i in range(0, len(news_items), chunk_size)]
            session_tokens = {}
            all_parsed = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=len(valid_apis)) as executor:
                futures = [executor.submit(self._process_chunk, c, config, key_queue, session_tokens) for c in chunks]
                for f in concurrent.futures.as_completed(futures):
                    if res := f.result(): all_parsed.extend(res)

            if all_parsed:
                # 判定这是否是一次更新
                is_update = os.path.exists(os.path.join(DB_DIR, f"daily_{date_str}.json"))
                exporter.update_database(date_str, all_parsed)
                
                with open(os.path.join(DB_DIR, f"daily_{date_str}.json"), 'r', encoding='utf-8') as f:
                    full_day_items = json.load(f)
                exporter.render_report("Daily", date_str, full_day_items, config, is_update=is_update)

                tot = sum(session_tokens.values())
                log_msg = "📊 本批次处理完毕！账单：\n"
                for k, v in sorted(session_tokens.items()):
                    if v > 0: log_msg += f"  - {k} 已消耗: {v:,} tokens\n"
                log_msg += f"  > 💰 批次总消耗: {tot:,} tokens | 全局累计: {config['total_tokens']:,} tokens"
                self.log_callback(log_msg)

            try: os.remove(target_file)
            except: pass

    def _check_periodic_reports(self, exporter, config):
        now = datetime.now()

        # Weekly logic
        if config.get('enable_weekly', True) and now.weekday() == 0 and now.hour >= 16:
            last_mon = now - timedelta(days=now.weekday() + 7)
            last_sun = now - timedelta(days=now.weekday() + 1)
            label = f"{last_mon.strftime('%Y-%m-%d')}_to_{last_sun.strftime('%Y-%m-%d')}"
            weekly_pdf = os.path.join(config['save_path'], f"WeeklyNews_{label}.pdf")

            needs_update = False
            items = []
            db_mod_times = []
            for i in range(7):
                day = last_mon + timedelta(days=i)
                db_path = os.path.join(DB_DIR, f"daily_{day.strftime('%Y-%m-%d')}.json")
                if os.path.exists(db_path):
                    with open(db_path, 'r', encoding='utf-8') as f: items.extend(json.load(f))
                    db_mod_times.append(os.path.getmtime(db_path))

            if items:
                is_update = False
                if not os.path.exists(weekly_pdf): needs_update = True
                else:
                    pdf_mod_time = os.path.getmtime(weekly_pdf)
                    if any(t > pdf_mod_time for t in db_mod_times):
                        needs_update = True
                        is_update = True

                if needs_update:
                    self.log_callback(f"📅 正在合并生成上周周报...")
                    exporter.render_report("Weekly", label, items, config, is_update=is_update)

        # Monthly logic
        if config.get('enable_monthly', True) and now.day >= 5 and now.hour >= 8:
            first_this_month = now.replace(day=1)
            last_last_month = first_this_month - timedelta(days=1)
            label = last_last_month.strftime("%Y-%b") 
            monthly_pdf = os.path.join(config['save_path'], f"MonthlyNews_{label}.pdf")

            needs_update = False
            items = []
            db_mod_times = []
            for i in range(1, last_last_month.day + 1):
                day = last_last_month.replace(day=i)
                db_path = os.path.join(DB_DIR, f"daily_{day.strftime('%Y-%m-%d')}.json")
                if os.path.exists(db_path):
                    with open(db_path, 'r', encoding='utf-8') as f: items.extend(json.load(f))
                    db_mod_times.append(os.path.getmtime(db_path))

            if items:
                is_update = False
                if not os.path.exists(monthly_pdf): needs_update = True
                else:
                    pdf_mod_time = os.path.getmtime(monthly_pdf)
                    if any(t > pdf_mod_time for t in db_mod_times):
                        needs_update = True
                        is_update = True

                if needs_update:
                    self.log_callback(f"📅 正在合并生成上月月报...")
                    exporter.render_report("Monthly", label, items, config, is_update=is_update)
                
    def stop(self): self.is_running = False