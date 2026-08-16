# -*- coding: utf-8 -*-
"""通用纯函数工具：JSON 数组提取、时间归一化、重试退避。

从 pipelines.py 拆出的无状态工具，供 fetcher / analyzer / exporter 复用，可直接单测。
"""
import json
import re
from datetime import timezone


def to_utc_aware(dt):
    """将任意 datetime 归一化为带 UTC 时区的 aware datetime。
    naive（RSS 省略时区）按 RSS/feedparser 惯例视为 UTC。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def retry_backoff(retry_count):
    """递增退避秒数：分析失败标记重试时的间隔，避免连接不畅时高频重试烧资源。
    30s → 1min → 2min → 5min → 10min（封顶）。"""
    delays = [30, 60, 120, 300, 600]
    return delays[min(max(retry_count - 1, 0), len(delays) - 1)]


def extract_json_array(text):
    """从 LLM 返回文本中提取 JSON 数组：遍历所有 [...{...}...] 候选，
    返回**最后一个**能成功 json.loads 的数组。
    - 普通模型：正文只有一个 JSON 数组 → 直接命中；
    - Qwen/DeepSeek 等推理模型：草稿/编号注释（`[1] {...}`）不会命中正则，
      最终答案数组在 reasoning_content 末尾 → 取到完整结果。
    无有效数组返回 None。"""
    result = None
    for m in re.finditer(r'\[\s*\{.*?\}\s*\]', text, re.DOTALL):
        try:
            arr = json.loads(m.group(0))
            if isinstance(arr, list):
                result = arr
        except Exception:
            continue
    return result


def date_from_utc_time(t):
    """从 'UTC YYYY-MM-DD HH:MM' 提取日期 YYYY-MM-DD；失败返回 None（聚合路由兜底用）。"""
    if not t:
        return None
    s = str(t).strip()
    if s.upper().startswith('UTC '):
        s = s[4:].strip()
    try:
        return s[:10] if len(s) >= 10 else None
    except Exception:
        return None
