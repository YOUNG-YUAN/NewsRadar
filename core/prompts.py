# -*- coding: utf-8 -*-
"""提示词构造（纯函数）。

从 pipelines.py 拆出：分析提示词与具体 API / 线程解耦，便于单测与将来扩展
（如标题速译模式、深度分析模式、按栏目分组分析等在此新增 build_xxx_prompt）。
"""


def build_analysis_prompt(config):
    """构造「情报分析师」分析提示词：要求严格 JSON 数组 + 16 个标准栏目 + 照抄字段。"""
    user_prompt = config.get("user_prompt", "").strip()
    interest_focus = f"重点关注以下领域：{user_prompt}" if user_prompt else "重点关注：AI大模型、地缘政治、科技巨头商业动态"
    output_lang = config.get("language", "zh")
    lang_instruction = "必须使用 简体中文 (Simplified Chinese) 输出摘要和翻译标题。" if output_lang == "zh" else "You MUST output the summary and translated_title in English."

    return f"""你是一位情报分析师。分析这批外媒新闻。
    【关注焦点】(判定 is_priority 为 true 的标准)：{interest_focus}
    【可选的栏目大类 (必须且只能使用以下名称)】：
    中国 (China) | 美国 (U.S.) | 亚洲 (Asia) | 欧洲 (Europe) | 世界 (World) | 商业 (Business) | 市场与金融 (Markets & Finance) | 人工智能与机器人 (AI & Robotics) | 科技 (Tech) | 科学 (Science) | 健康 (Health) | 能源 (Energy) | 环境与气候 (Environment & Climate) | 生活 (Lifestyle) | 文艺 (Arts & Culture) | 体育 (Sports)
    【严格纪律】：
    1. 必须完全照抄我提供的 source, time 和 url，不可修改为“未提供”。
    2. {lang_instruction}
    必须以严格的 JSON 数组格式返回结果。
    示例: [{{"is_priority": true, "translated_title": "...", "original_title": "...", "keywords": ["..."], "summary": "...", "categories": ["..."], "source": "原样提取的来源", "time": "原样提取的时间", "url": "原样提取的链接"}}]
    """


def build_connect_test_prompt():
    """连接测试用的极简提示词（尽量让模型快速回复，避免过度思考）。"""
    return "To test if the API connection is normal, please reply 'ok'."
