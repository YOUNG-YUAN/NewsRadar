import os
import json
import time
import requests
import feedparser
import threading
import concurrent.futures
import queue
import re
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from openai import OpenAI
from dateutil import parser as date_parser

from .config_mgr import ConfigManager, RAW_DIR, FAILED_DIR
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
                if not self.is_running: 
                    break
                if self.is_paused: 
                    break 
                if not src.get('checked', False): 
                    continue
                
                self.log_callback(f"正在获取: {src['name']}...")
                feed_data = None
                
                for attempt in range(1, 4):
                    if not self.is_running or self.is_paused: 
                        break
                    try:
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

                if not feed_data: 
                    continue
                    
                for entry in feed_data.entries:
                    link = entry.link
                    if link not in history:
                        is_valid_time = is_fetch_all
                        if not is_valid_time:
                            try:
                                pub_time = date_parser.parse(entry.published)
                                if start_time_utc <= pub_time <= end_time_utc: 
                                    is_valid_time = True
                            except Exception: 
                                pass 
                                
                        if is_valid_time:
                            desc = BeautifulSoup(entry.description, "html.parser").get_text() if hasattr(entry, 'description') else ""
                            try: 
                                display_time = date_parser.parse(entry.published).strftime("%Y-%m-%d %H:%M")
                            except: 
                                display_time = intercept_display

                            all_new_items_this_session.append({
                                "source": src['name'], 
                                "title": entry.title,
                                "description": desc[:300], 
                                "url": link, 
                                "time": display_time
                            })
                            ConfigManager.add_to_history(link)
                            history.add(link)

            if not self.is_paused:
                if all_new_items_this_session:
                    try:
                        chunk_size = int(config.get('batch_size', '30'))
                        if chunk_size <= 0: chunk_size = 30
                    except: 
                        chunk_size = 30
                        
                    for idx, i in enumerate(range(0, len(all_new_items_this_session), chunk_size)):
                        chunk_items = all_new_items_this_session[i:i + chunk_size]
                        batch_data = {
                            "session_timestamp": session_timestamp, 
                            "intercept_display": intercept_display, 
                            "news_list": chunk_items
                        }
                        batch_file = os.path.join(RAW_DIR, f"temp_RSS_batch_{session_timestamp}_{idx}.json")
                        with open(batch_file, 'w', encoding='utf-8') as f:
                            json.dump(batch_data, f, ensure_ascii=False)
                    self.log_callback(f"获取完成！{len(all_new_items_this_session)} 条资讯已分拆送入AI队列。")
                else:
                    self.log_callback("当前周期无新资讯更新。")

            for _ in range(sleep_secs):
                if not self.is_running: break
                while self.is_paused and self.is_running: 
                    time.sleep(1) 
                time.sleep(1)

    def stop(self): 
        self.is_running = False


class AnalyzerThread(threading.Thread):
    def __init__(self, log_callback, token_callback):
        super().__init__()
        self.log_callback = log_callback
        self.token_callback = token_callback
        self.is_running = True
        self.is_paused = False
        self.daemon = True
        self.token_lock = threading.Lock()

    def _process_single_chunk(self, chunk_file, config, key_queue, session_tokens):
        if not self.is_running or self.is_paused: 
            return None, None
        
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
                session_timestamp = batch_data["session_timestamp"]
                intercept_display = batch_data["intercept_display"]
                current_chunk = batch_data["news_list"]
        except Exception as e:
            self.log_callback(f"读取临时文件失败: {e}")
            try: os.remove(chunk_file) 
            except: pass
            return None, None

        # 🌟 从队列获取独立配置
        api_name, api_config = key_queue.get()
        self.log_callback(f"🚀 [{api_name}] 接单，开始分析: {os.path.basename(chunk_file)}")

        text_data = ""
        for i, n in enumerate(current_chunk):
            text_data += f"[{i+1}] 标题:{n['title']}\n"
            text_data += f"来源:{n['source']} | 时间:{n['time']}\n"
            text_data += f"简介:{n['description']}\n"
            text_data += f"链接:{n['url']}\n\n"

        user_prompt = config.get("user_prompt", "").strip()
        interest_focus = f"重点关注以下领域：{user_prompt}" if user_prompt else "重点关注：AI大模型、地缘政治、科技巨头商业动态"

        output_lang = config.get("language", "zh")
        lang_instruction = "必须使用 简体中文 (Simplified Chinese) 输出摘要和翻译标题。" if output_lang == "zh" else "You MUST output the summary and translated_title in English."

        prompt = f"""
        你是一位情报分析师。分析这批外媒新闻。
        【关注焦点】(判定 is_priority 为 true 的标准)：{interest_focus}
        【可选的栏目大类 (必须且只能使用以下名称)】：
        中国 (China) | 美国 (U.S.) | 亚洲 (Asia) | 欧洲 (Europe) | 世界 (World) | 商业 (Business) | 市场与金融 (Markets & Finance) | 人工智能与机器人 (AI & Robotics) | 科技 (Tech) | 科学 (Science) | 健康 (Health) | 能源 (Energy) | 环境与气候 (Environment & Climate) | 生活 (Lifestyle) | 文艺 (Arts & Culture) | 体育 (Sports)
        
        【严格纪律】：
        1. 必须完全照抄我提供的 source(来源)、time(时间) 和 url(链接)，绝对不可省略或修改为“未提供”。
        2. {lang_instruction}
        
        必须以严格的 JSON 数组格式返回结果。
        示例: [{{"is_priority": true, "translated_title": "...", "original_title": "...", "keywords": ["..."], "summary": "...", "categories": ["..."], "source": "原样提取的来源", "time": "原样提取的时间", "url": "原样提取的链接"}}]
        """

        for attempt in range(1, 4):
            if not self.is_running or self.is_paused: 
                key_queue.put((api_name, api_config))
                key_queue.task_done()
                return None, None
            
            try:
                # 🌟 读取独立方块的配置
                provider = api_config.get('provider', 'Google Gemini')
                url = api_config.get('url', '')
                model_name = api_config.get('model', '')
                current_api_key = api_config.get('api_key', '')

                proxies = None
                if config.get('ai_use_proxy', False):
                    proxy_srv = config.get('ai_proxy_server', 'http://127.0.0.1')
                    if not proxy_srv.startswith('http'): 
                        proxy_srv = 'http://' + proxy_srv
                    proxy_url = f"{proxy_srv}:{config.get('ai_proxy_port', '10808')}"
                    proxies = {'http': proxy_url, 'https': proxy_url}
                    os.environ['HTTP_PROXY'], os.environ['HTTPS_PROXY'] = proxy_url, proxy_url
                else:
                    os.environ.pop('HTTP_PROXY', None)
                    os.environ.pop('HTTPS_PROXY', None)

                if provider == "Google Gemini":
                    headers = {"Content-Type": "application/json"}
                    data = {"systemInstruction": {"parts": [{"text": prompt}]}, "contents": [{"parts": [{"text": text_data}]}]}
                    base = url.strip().rstrip('/')
                    if not base.endswith('models'): 
                        base = f"{base}/models"
                    full_url = f"{base}/{model_name}:generateContent?key={current_api_key}"
                    
                    resp = requests.post(full_url, headers=headers, json=data, proxies=proxies, timeout=120)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    
                    if 'candidates' in resp_json and resp_json['candidates']:
                        result_text = resp_json['candidates'][0]['content']['parts'][0]['text']
                    else:
                        raise ValueError(f"Gemini 返回异常: {resp_json}")
                    tokens_used = resp_json.get('usageMetadata', {}).get('totalTokenCount', int((len(text_data) + len(result_text)) * 0.8))
                
                else:
                    client = OpenAI(api_key=current_api_key, base_url=url)
                    resp = client.chat.completions.create(
                        model=model_name, 
                        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text_data}], 
                        temperature=0.1
                    )
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
                    self.log_callback(f"✅ [{api_name}] 成功完成，解析出 {len(parsed_items)} 条情报！")
                    os.remove(chunk_file)
                    
                    key_queue.put((api_name, api_config))
                    key_queue.task_done()
                    return session_timestamp, {"intercept_display": intercept_display, "items": parsed_items}
                else: 
                    raise ValueError("JSON 解析失败。")

            except Exception as e:
                if attempt < 3:
                    self.log_callback(f"⚠️ [{api_name}] 分析失败 (尝试 {attempt}/3)...等待重试")
                    time.sleep(2)
                else:
                    self.log_callback(f"❌ [{api_name}] 彻底失败: {str(e)[:50]}")
                    try: 
                        os.rename(chunk_file, os.path.join(FAILED_DIR, os.path.basename(chunk_file)))
                    except: 
                        pass
                    
                    key_queue.put((api_name, api_config))
                    key_queue.task_done()
                    return None, None

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
                sid = f_name.split('_')[3]
                sessions_dict.setdefault(sid, []).append(os.path.join(RAW_DIR, f_name))

            current_session = sorted(sessions_dict.keys())[0]
            all_json_items, intercept_display = [], ""
            
            # 🌟 读取并组装并发 API 矩阵
            is_multi = config.get('is_multi_mode', False)
            active_apis = config.get('multi_apis', [])
            
            if not active_apis:
                fallback_prov = config.get('ai_provider', 'Google Gemini')
                active_apis = [{
                    'provider': fallback_prov,
                    'url': config.get('providers', {}).get(fallback_prov, {}).get('url', ''),
                    'model': config.get('providers', {}).get(fallback_prov, {}).get('model', ''),
                    'api_key': config.get('providers', {}).get(fallback_prov, {}).get('api_key', '')
                }]

            if not is_multi:
                active_apis = [active_apis[0]]

            # 过滤掉没填 API Key 的空槽位
            valid_apis = [api for api in active_apis if api.get('api_key', '').strip()]
            
            if not valid_apis:
                self.log_callback("❌ 错误：未配置有效的 API Key，无法进行 AI 分析。")
                time.sleep(5)
                continue
                
            key_queue = queue.Queue()
            for idx, api in enumerate(valid_apis):
                key_queue.put((f"API-{idx+1}", api))
                
            session_tokens = {}
            max_workers = key_queue.qsize() if key_queue.qsize() > 0 else 1

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(self._process_single_chunk, fp, config, key_queue, session_tokens): fp for fp in sessions_dict[current_session]}
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res and res[1]: 
                        intercept_display = res[1]["intercept_display"]
                        all_json_items += res[1]["items"]

            if all_json_items:
                total_session_tokens = sum(session_tokens.values())
                log_msg = "📊 本批次流水线处理完毕！账单明细：\n"
                for k_name in sorted(session_tokens.keys()):
                    if session_tokens[k_name] > 0:
                        log_msg += f"  - {k_name} 已消耗: {session_tokens[k_name]:,} tokens\n"
                log_msg += f"  > 💰 本批次总消耗: {total_session_tokens:,} tokens\n"
                log_msg += f"  > 🏦 全局累计总计: {config['total_tokens']:,} tokens"
                self.log_callback(log_msg)

                # 🌟 调用渲染引擎
                exporter = ReportExporter(self.log_callback)
                exporter.export_all(current_session, intercept_display, all_json_items, config)
                
    def stop(self): 
        self.is_running = False