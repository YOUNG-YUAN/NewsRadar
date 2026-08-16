# -*- coding: utf-8 -*-
"""兼容层：按模块拆分后的重导出（保持 `from core.pipelines import ...` 旧写法可用）。

实际实现已拆分为：
  - core/fetcher.py    → FetcherThread（流水线1：抓取）
  - core/analyzer.py   → AnalyzerThread（流水线2：分析 + 故障转移 + 聚合路由）
  - core/llm_client.py → 统一 LLM 调用（三分支/代理/推理回退/disable_thinking）
  - core/prompts.py    → 提示词构造
  - core/parsing.py    → 纯函数工具（JSON 提取 / 时间 / 退避）
"""
from .parsing import to_utc_aware, retry_backoff, extract_json_array, date_from_utc_time
from .fetcher import FetcherThread
from .analyzer import AnalyzerThread

# 兼容旧下划线命名（旧代码/internal 引用）
_extract_json_array = extract_json_array
_retry_backoff = retry_backoff
_date_from_utc_time = date_from_utc_time
