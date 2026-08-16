# -*- coding: utf-8 -*-
"""流水线1：FetcherThread —— 并发抓取 RSS、URL 去重、按 UTC 日期落盘 raw 批次。

从 pipelines.py 拆出（职责：抓取线程生命周期 + RSS 抓取 + 时间窗口过滤 + 去重写盘）。
"""
import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .config_mgr import ConfigManager, RAW_DIR
from .parsing import to_utc_aware


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

    def _fetch_single_source(self, src, headers, rss_proxies):
        if not self.is_running or self.is_paused: return None
        for attempt in range(1, 4):
            if not self.is_running or self.is_paused: return None
            try:
                res = requests.get(src['url'], headers=headers, proxies=rss_proxies, timeout=15)
                res.raise_for_status()
                temp_feed = feedparser.parse(res.content)
                if temp_feed.bozo and not temp_feed.entries:
                    raise ValueError(f"解析失败")
                return (src, temp_feed)
            except Exception as e:
                if attempt < 3:
                    time.sleep(2)
                else:
                    err_msg = str(e).split('\n')[0][:40]
                    self.log_callback(f"❌ 获取 {src['name']} 彻底失败: {err_msg}...")
        return None

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
            new_links_to_save = []

            active_sources = [s for s in sources if s.get('checked', False)]

            if active_sources and not self.is_paused:
                max_workers = min(20, len(active_sources))
                self.log_callback(f"⚡ 启动并发抓取引擎 (并发数: {max_workers})...")

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(self._fetch_single_source, src, headers, rss_proxies) for src in active_sources]

                    for f in as_completed(futures):
                        if not self.is_running or self.is_paused: break
                        res = f.result()
                        if res:
                            src, feed_data = res
                            source_new_count = 0 # 🌟 新增：统计单个源截获的有效新资讯数量

                            for entry in feed_data.entries:
                                link = entry.link
                                if link not in history:
                                    is_valid_time = is_fetch_all
                                    pub_time_utc = None
                                    if not is_valid_time:
                                        try:
                                            pub_time = date_parser.parse(entry.published)
                                            pub_time_utc = to_utc_aware(pub_time)
                                            if start_time_utc <= pub_time_utc <= end_time_utc: is_valid_time = True
                                        except: pass

                                    if is_valid_time:
                                        desc = BeautifulSoup(entry.description, "html.parser").get_text() if hasattr(entry, 'description') else ""
                                        try:
                                            if not pub_time_utc: pub_time_utc = to_utc_aware(date_parser.parse(entry.published))
                                            display_time = f"UTC {pub_time_utc.strftime('%Y-%m-%d %H:%M')}"
                                            date_str = pub_time_utc.strftime("%Y-%m-%d")
                                        except:
                                            dt_now = datetime.now(timezone.utc)
                                            display_time = f"UTC {dt_now.strftime('%Y-%m-%d %H:%M')}"
                                            date_str = dt_now.strftime("%Y-%m-%d")

                                        date_groups.setdefault(date_str, []).append({
                                            "source": src['name'],
                                            "title": entry.title,
                                            "description": desc[:300],
                                            "url": link,
                                            "time": display_time
                                        })
                                        history.add(link)
                                        new_links_to_save.append(link)
                                        fetched_count += 1
                                        source_new_count += 1 # 🌟 累加当前源的有效获取量

                            # 🌟 恢复：单源抓取完毕后的汇报日志 (包含战果)
                            self.log_callback(f"📡 {src['name']} 扫描完毕 (截获 {source_new_count} 条新资讯)")

            if not self.is_paused:
                if new_links_to_save:
                    ConfigManager.append_history(new_links_to_save)

                if fetched_count > 0:
                    for d_str, items in date_groups.items():
                        batch_file = os.path.join(RAW_DIR, f"raw_{d_str}_{uuid.uuid4().hex[:8]}.json")
                        with open(batch_file, 'w', encoding='utf-8') as f:
                            json.dump({"date": d_str, "news": items}, f, ensure_ascii=False)
                    self.log_callback(f"✅ 抓取阶段结束，共截获 {fetched_count} 条新资讯。")
                else:
                    self.log_callback("当前周期无新资讯更新。")

            for _ in range(sleep_secs):
                if not self.is_running: break
                while self.is_paused and self.is_running: time.sleep(1)
                time.sleep(1)

    def stop(self): self.is_running = False
