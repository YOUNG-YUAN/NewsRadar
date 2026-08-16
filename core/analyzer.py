# -*- coding: utf-8 -*-
"""流水线2：AnalyzerThread —— 聚合 raw/retry 批次 → 批量 LLM 分析（带故障转移）→ 按日期路由数据湖 → 渲染日报。

从 pipelines.py 拆出（职责：分析线程生命周期 + 编排 + 故障转移状态；无状态纯逻辑
已下沉到 llm_client / prompts / parsing）。
"""
import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config_mgr import ConfigManager, RAW_DIR, FAILED_DIR, DB_DIR
from .exporter import ReportExporter
from .parsing import extract_json_array, retry_backoff, date_from_utc_time
from .prompts import build_analysis_prompt
from .llm_client import call_llm, build_proxy


class AnalyzerThread(threading.Thread):
    def __init__(self, log_callback, token_callback, fetcher_ref=None):
        super().__init__()
        self.log_callback = log_callback
        self.token_callback = token_callback
        self.fetcher_ref = fetcher_ref
        self.is_running = True
        self.is_paused = False
        self.daemon = True
        self.token_lock = threading.Lock()

        self.round_active = False
        self.session_news_count = 0
        self.session_token_count = 0
        self.session_updated_dates = set()

        self.last_history_scan_time = 0
        self._next_retry_time = 0  # 🌟 待重试批次的下一次可重试时间戳（退避控制）

        # 🌟 多 API 故障转移状态：记录每个 API 的惩罚截止时间（最近一次使用失败 → 10 分钟内不接单）
        self._api_penalty = {}
        self._api_lock = threading.Lock()

    # ---------- 多 API 故障转移辅助 ----------
    def _is_api_penalized(self, api_name):
        with self._api_lock:
            return self._api_penalty.get(api_name, 0) > time.time()

    def _mark_api_fail(self, api_name):
        """API 连续失败 → 标记异常，10 分钟内不接单。"""
        with self._api_lock:
            self._api_penalty[api_name] = time.time() + 600

    def _mark_api_ok(self, api_name):
        with self._api_lock:
            self._api_penalty.pop(api_name, None)

    def _acquire_api(self, key_queue, timeout=120):
        """从队列取一个「未惩罚」的正常 API（最近一次使用未失败 / 从未失败过）。
        惩罚中的 API 直接淘汰（不归还队列）；超时/空返回 None。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                api = key_queue.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                return None
            name, cfg = api
            if not self._is_api_penalized(name):
                return api
            key_queue.task_done()  # 惩罚中的 API 淘汰，不归还

    def _process_chunk(self, chunk_items, config, key_queue, session_tokens):
        if not self.is_running or self.is_paused: return None

        text_data = ""
        for i, n in enumerate(chunk_items):
            text_data += f"[{i+1}] 标题:{n['title']}\n来源:{n['source']} | 时间:{n['time']}\n简介:{n['description']}\n链接:{n['url']}\n\n"

        prompt = build_analysis_prompt(config)
        proxies, proxy_url = build_proxy(config)

        # 🌟 故障转移：某 API 连续 2 次失败 → 标记异常（10 分钟不接单）→ 转交下一个正常 API
        while self.is_running and not self.is_paused:
            acquired = self._acquire_api(key_queue)
            if acquired is None:
                self.log_callback("⚠️ 无可用正常 API，本批次保留待稍后重试")
                return None
            api_name, api_config = acquired
            self.log_callback(f"🚀 [{api_name}] 接单，分析任务单元 (共 {len(chunk_items)} 条)...")

            for attempt in (1, 2):  # 🌟 每个 API 最多 2 次尝试（原 3 次）
                if not self.is_running or self.is_paused:
                    key_queue.put(acquired); key_queue.task_done()
                    return None
                try:
                    self.log_callback(f"⏳ [{api_name}] 正在调用 {api_config.get('provider')} ({api_config.get('model')}) 分析 {len(chunk_items)} 条新闻...")
                    result_text, tokens_used = call_llm(
                        api_config, prompt, text_data, proxies=proxies, proxy_url=proxy_url,
                        log_callback=lambda m: self.log_callback(f"🧠 [{api_name}] {m}"),
                    )
                    with self.token_lock:
                        session_tokens[api_name] = session_tokens.get(api_name, 0) + tokens_used
                        self.session_token_count += tokens_used
                        config['total_tokens'] += tokens_used
                        self.token_callback(config['total_tokens'])

                    clean_json_str = result_text.replace("```json", "").replace("```", "").strip()
                    parsed_items = extract_json_array(clean_json_str)
                    if parsed_items is not None:
                        self._mark_api_ok(api_name)  # 🌟 成功 → 恢复正常状态
                        key_queue.put(acquired); key_queue.task_done()
                        return parsed_items
                    else:
                        raise ValueError("JSON 解析失败。")
                except Exception as e:
                    # 🌟 每次重试都打日志，避免"接单后长时间无动静"
                    self.log_callback(f"⚠️ [{api_name}] 第 {attempt}/2 次调用失败: {str(e)[:60]}")
                    if attempt < 2: time.sleep(2)

            # 2 次都失败 → 惩罚该 API（10 分钟不接单），不归还队列，循环转交下一个正常 API
            self._mark_api_fail(api_name)
            self.log_callback(f"❌ [{api_name}] 连续 2 次失败，标记异常（10 分钟内不接单），转交其他正常 API...")

        return None

    def run(self):
        self.log_callback("流水线2 (增量情报分析) 已启动...")
        exporter = ReportExporter(self.log_callback)

        while self.is_running:
            if self.is_paused:
                time.sleep(1); continue

            raw_files = [os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR) if f.startswith('raw_') and f.endswith('.json')]
            retry_files = []
            if time.time() >= self._next_retry_time:
                retry_files = [os.path.join(FAILED_DIR, f) for f in os.listdir(FAILED_DIR) if f.startswith('retry_') and f.endswith('.json')]
            # 🌟 优先处理 fresh 批次，其次处理待重试批次
            pending_files = sorted(raw_files) + sorted(retry_files)

            if not pending_files:
                if self.round_active and self.fetcher_ref and not self.fetcher_ref.is_alive():
                    self._print_session_summary()
                    self.round_active = False
                    time.sleep(5)

                if getattr(self, 'manual_scan_requested', False):
                    self.log_callback("⚙️ [收到指令] 正在全量扫描数据湖，合并生成周报/月报...")
                    self._check_periodic_reports(exporter, ConfigManager.load_config())
                    self.log_callback("✅ 历史数据扫描与报表生成执行完毕！")
                    self.manual_scan_requested = False
                    time.sleep(2)
                else:
                    time.sleep(3)
                continue

            if not self.round_active:
                self.round_active = True
                self.session_news_count = 0
                self.session_token_count = 0
                self.session_updated_dates.clear()

            config = ConfigManager.load_config()

            # 🌟 聚合所有待处理文件（raw 优先、retry 在后）为一个池，按来源日期路由——
            #    避免小批次（如恢复的 .bak 只有 1-2 条）逐条调用 LLM 浪费时间
            agg_items = []
            src_date_by_url = {}   # url -> 来源日期（路由到对应 daily_*.json）
            max_retry = 0
            to_delete = []
            for p in pending_files:
                try:
                    with open(p, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    try: os.remove(p)
                    except: pass
                    continue
                d = data.get('date', '')
                rc = int(data.get('retry_count', 0) or 0)
                max_retry = max(max_retry, rc)
                for it in data.get('news', []):
                    u = it.get('url')
                    if u: src_date_by_url[u] = d
                    agg_items.append(it)
                to_delete.append(p)
                if p.startswith(FAILED_DIR):
                    self.log_callback(f"🔁 聚合 {len(data.get('news', []))} 条待重试条目（第 {rc} 次标记）...")

            if not agg_items:
                continue

            self.session_news_count += len(agg_items)

            active_apis = config.get('multi_apis', [])
            if not config.get('is_multi_mode', False) or not active_apis:
                fp = config.get('ai_provider', 'Google Gemini')
                active_apis = [{'provider': fp, 'url': config.get('providers', {}).get(fp, {}).get('url', ''), 'model': config.get('providers', {}).get(fp, {}).get('model', ''), 'api_key': config.get('providers', {}).get(fp, {}).get('api_key', '')}]

            # 🌟 只使用"已启用 且 有 api_key"的节点（enabled 缺省视为启用，兼容旧配置）
            valid_apis = [api for api in active_apis if api.get('enabled', True) and api.get('api_key', '').strip()]
            if not valid_apis:
                self.log_callback("❌ 错误：未配置有效的 API Key，无法进行 AI 分析。")
                time.sleep(5); continue

            # 🌟 只放入未惩罚的正常 API（最近一次使用未失败）；全部在惩罚期则等待恢复
            key_queue = queue.Queue()
            for idx, api in enumerate(valid_apis):
                name = f"API-{idx+1}"
                if not self._is_api_penalized(name):
                    key_queue.put((name, api))
            if key_queue.empty():
                self.log_callback("⏳ 所有 API 均在 10 分钟惩罚期内，等待恢复后继续...")
                time.sleep(5); continue

            try: chunk_size = int(config.get('batch_size', '30'))
            except: chunk_size = 30
            if chunk_size <= 0: chunk_size = 30

            # 🌟 跨文件聚合后按 batch_size 切块，尽量凑满每批条数
            chunks = [agg_items[i:i + chunk_size] for i in range(0, len(agg_items), chunk_size)]

            session_tokens = {}
            all_parsed = []

            failed_chunks = []   # 🌟 记录分析失败（如 stream timeout）的 chunk，标记待重试
            with ThreadPoolExecutor(max_workers=len(valid_apis)) as executor:
                future_to_chunk = {executor.submit(self._process_chunk, c, config, key_queue, session_tokens): c for c in chunks}
                for f in as_completed(future_to_chunk):
                    res = f.result()
                    if res:
                        all_parsed.extend(res)
                    else:
                        failed_chunks.append(future_to_chunk[f])

            # 🌟 每批次结束统一持久化一次 token 计数（替代原先每请求写文件，避免并发写竞争）
            ConfigManager.save_config(config)

            # 🌟 失败不丢弃：按来源日期分组写入 FAILED_DIR，连接通畅后由下一轮自动重试
            if failed_chunks:
                fail_items = [item for chunk in failed_chunks for item in chunk]
                by_fail_date = {}
                for it in fail_items:
                    d = src_date_by_url.get(it.get('url')) or 'unknown'
                    by_fail_date.setdefault(d, []).append(it)
                backoff = retry_backoff(max_retry + 1)
                for d, items in by_fail_date.items():
                    try:
                        retry_file = os.path.join(FAILED_DIR, f"retry_{d}_{uuid.uuid4().hex[:8]}.json")
                        with open(retry_file, 'w', encoding='utf-8') as f:
                            json.dump({"date": d, "news": items, "retry_count": max_retry + 1}, f, ensure_ascii=False)
                    except Exception as e:
                        self.log_callback(f"❌ 写入待重试文件失败: {e}")
                self._next_retry_time = time.time() + backoff
                self.log_callback(f"⏳ {len(fail_items)} 条分析失败（第 {max_retry + 1} 次标记），已保留待连接通畅后自动重试（{backoff} 秒后）")

            # 🌟 成功：按来源日期路由进数据湖，逐个日期渲染日报
            if all_parsed:
                by_date = {}
                for item in all_parsed:
                    d = src_date_by_url.get(item.get('url')) or date_from_utc_time(item.get('time')) or 'unknown'
                    by_date.setdefault(d, []).append(item)
                for d, items in by_date.items():
                    db_path = os.path.join(DB_DIR, f"daily_{d}.json")
                    is_update = os.path.exists(db_path)
                    exporter.update_database(d, items)
                    if os.path.exists(db_path):
                        try:
                            with open(db_path, 'r', encoding='utf-8') as f:
                                full_day_items = json.load(f)
                            exporter.render_report("Daily", d, full_day_items, config, is_update=is_update)
                            self.session_updated_dates.add(d)
                        except Exception as e:
                            self.log_callback(f"❌ 读取数据湖失败: {e}")
                    else:
                        self.log_callback(f"⚠️ 无法渲染 {d} 的日报：数据合并发生异常。")

                tot = sum(session_tokens.values())
                if tot > 0:
                    log_msg = "📊 本日份数据处理完毕！账单：\n"
                    for k, v in sorted(session_tokens.items()):
                        if v > 0: log_msg += f"  - {k} 已消耗: {v:,} tokens\n"
                    log_msg += f"  > 💰 本日总计: {tot:,} tokens | 全局累计: {config['total_tokens']:,} tokens"
                    self.log_callback(log_msg)

            # 🌟 聚合后一次清理已处理文件
            for p in to_delete:
                try: os.remove(p)
                except: pass

    def _print_session_summary(self):
        daily_count = len(self.session_updated_dates)

        summary = [
            f"\n🏁 【本轮监听任务已全部达成】",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"📈 成果统计：共截获 {self.session_news_count} 条资讯，更新/生成了 {daily_count} 份日报。",
            f"💰 账单统计：本轮监听轮次共消耗 {self.session_token_count:,} tokens。",
            f"💤 状态更新：所有简报已入库。系统进入休眠，等待下一轮采样周期。",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        ]
        for line in summary:
            self.log_callback(line)

    def _check_periodic_reports(self, exporter, config):
        now = datetime.now()

        all_dbs = [f for f in os.listdir(DB_DIR) if f.startswith('daily_') and f.endswith('.json')]
        if not all_dbs: return

        available_dates = sorted([f.replace('daily_', '').replace('.json', '') for f in all_dbs])

        if config.get('enable_weekly', True):
            weeks_map = {}
            for d_str in available_dates:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
                monday = dt - timedelta(days=dt.weekday())
                sunday = monday + timedelta(days=6)
                week_label = f"{monday.strftime('%Y-%m-%d')}_to_{sunday.strftime('%Y-%m-%d')}"
                weeks_map.setdefault(week_label, []).append(d_str)

            for label, days in weeks_map.items():
                monday_of_label = datetime.strptime(label.split('_to_')[0], "%Y-%m-%d")
                next_monday_16h = monday_of_label + timedelta(days=7, hours=16)

                if now < next_monday_16h: continue

                weekly_pdf = os.path.join(config['save_path'], f"WeeklyNews_{label}.pdf")
                self._generate_if_needed(exporter, config, "Weekly", label, days, weekly_pdf)

        if config.get('enable_monthly', True):
            months_map = {}
            for d_str in available_dates:
                label = d_str[:7]
                months_map.setdefault(label, []).append(d_str)

            for month_key, days in months_map.items():
                dt_month = datetime.strptime(month_key, "%Y-%m")
                display_label = dt_month.strftime("%Y-%b")

                first_of_next_month = (dt_month.replace(day=28) + timedelta(days=4)).replace(day=1)
                threshold = first_of_next_month + timedelta(days=4, hours=8)

                if now < threshold: continue

                monthly_pdf = os.path.join(config['save_path'], f"MonthlyNews_{display_label}.pdf")
                self._generate_if_needed(exporter, config, "Monthly", display_label, days, monthly_pdf)

    def _generate_if_needed(self, exporter, config, r_type, label, days, file_path):
        items = []
        latest_db_mtime = 0
        for d in days:
            db_p = os.path.join(DB_DIR, f"daily_{d}.json")
            if os.path.exists(db_p):
                latest_db_mtime = max(latest_db_mtime, os.path.getmtime(db_p))
                with open(db_p, 'r', encoding='utf-8') as f:
                    items.extend(json.load(f))

        if not items: return

        needs_gen = False
        is_update = False
        if not os.path.exists(file_path):
            needs_gen = True
        elif latest_db_mtime > os.path.getmtime(file_path):
            needs_gen = True
            is_update = True

        if needs_gen:
            self.log_callback(f"📅 正在合并生成{label}的{r_type}报告...")
            exporter.render_report(r_type, label, items, config, is_update=is_update)

    def stop(self): self.is_running = False
