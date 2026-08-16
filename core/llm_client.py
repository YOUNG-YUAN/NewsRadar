# -*- coding: utf-8 -*-
"""统一 LLM 调用客户端（单一事实来源）。

从 pipelines.py 的 _process_chunk 拆出：Gemini / Claude / OpenAI 兼容三分支、
代理、推理模型 reasoning_content 回退、disable_thinking、超时全部收拢在这里。
**pipelines 与 gui/dialog_ai.py 的连接测试共用本模块**——消除两套调用逻辑漂移
（曾导致 Claude 分支不一致、推理模型 content 空等"测试通过但实际不通"问题）。

约定：
  - `call_llm()` 只负责「调一次 API 并返回原始文本 + token 数」，失败抛异常由调用方重试；
  - 调用方负责日志前缀（如 [API-1]）、重试/故障转移、token 持久化。
"""
import httpx
import requests
from openai import OpenAI


def build_proxy(config):
    """根据 config 构造 (requests proxies dict, httpx proxy_url)；未开启代理返回 (None, None)。"""
    if not config.get('ai_use_proxy', False):
        return None, None
    proxy_srv = config.get('ai_proxy_server', 'http://127.0.0.1')
    if not proxy_srv.startswith('http'):
        proxy_srv = 'http://' + proxy_srv
    proxy_url = f"{proxy_srv}:{config.get('ai_proxy_port', '10808')}"
    return {'http': proxy_url, 'https': proxy_url}, proxy_url


def call_llm(api_config, prompt, text_data, proxies=None, proxy_url=None, log_callback=None):
    """调用单个 LLM API，返回 (result_text, tokens_used)。失败抛异常由调用方重试。

    :param api_config: {provider, url, model, api_key, disable_thinking?}
    :param proxies:   requests 风格代理字典（Gemini/Claude 用）
    :param proxy_url: httpx 代理字符串（OpenAI 兼容路径用）
    :param log_callback: 可选回调，接收不带前缀的提示文本（如推理回退说明）
    """
    provider = api_config.get('provider', 'Google Gemini')
    url = api_config.get('url', '')
    model_name = api_config.get('model', '')
    current_api_key = api_config.get('api_key', '')

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
        result_text = resp_json['candidates'][0]['content']['parts'][0]['text']
        tokens_used = resp_json.get('usageMetadata', {}).get('totalTokenCount', int((len(text_data) + len(result_text)) * 0.8))

    elif provider == "Claude":
        # Anthropic Messages API（对齐 GUI 测试逻辑）
        headers = {
            "x-api-key": current_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        data = {
            "model": model_name,
            "max_tokens": 4096,
            "system": prompt,
            "messages": [{"role": "user", "content": text_data}],
        }
        resp = requests.post(url, headers=headers, json=data, proxies=proxies, timeout=120)
        resp.raise_for_status()
        resp_json = resp.json()
        result_text = "".join(part.get("text", "") for part in resp_json.get("content", []) if part.get("type") == "text")
        usage = resp_json.get("usage", {})
        tokens_used = (usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0)
        if tokens_used <= 0:
            tokens_used = int((len(text_data) + len(result_text)) * 0.8)

    else:
        # OpenAI 兼容路径：代理/超时绑定在线程私有 httpx 客户端上，多线程互不干扰。
        # 超时 300s：兼容 Qwen/DeepSeek 等推理模型（思考 4000+ tokens 需 2 分钟以上）。
        http_client = httpx.Client(proxy=proxy_url, timeout=300.0) if proxy_url else None
        client = OpenAI(api_key=current_api_key, base_url=url, timeout=300.0, http_client=http_client)
        request_kwargs = dict(model=model_name, messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text_data}], temperature=0.1)
        # disable_thinking：qwen 系推理模型关掉思考后直接输出 content，秒级返回
        if api_config.get('disable_thinking', False):
            request_kwargs["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
        resp = client.chat.completions.create(**request_kwargs)
        message = resp.choices[0].message
        result_text = message.content or ""
        # 兼容推理模型：content 为空时答案可能在 reasoning_content（openai SDK 2.x 存于 message.model_extra）
        reasoning_text = ""
        extra = getattr(message, "model_extra", None) or {}
        if isinstance(extra, dict):
            reasoning_text = extra.get("reasoning_content") or ""
        if reasoning_text and not result_text.strip():
            if log_callback:
                log_callback("content 为空（推理模型），回退读取 reasoning_content")
            result_text = reasoning_text
        tokens_used = resp.usage.total_tokens if resp.usage else int((len(text_data) + len(result_text)) * 0.8)

    return result_text, tokens_used
