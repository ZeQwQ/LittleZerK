#!/usr/bin/env python3
"""
配置管理模块 - AI/天气预设 + 配置持久化
ver0.5
"""

import os
import json

# 应用版本号（唯一来源，CLI --version 与配置流程共用）
VERSION = "ver0.5"

# ─────────────────────────────────────────────────────────────
# AI 模型预设
# ─────────────────────────────────────────────────────────────
MODEL_PRESETS = {
    "minimax": {
        "name": "MiniMax",
        "regex": [r"minimaxi", r"minimax"],
        "base_url": "https://api.minimaxi.com/v1",
        "default_model": "MiniMax-Text-01",
        "models": ["MiniMax-Text-01", "abab6.5s-chat", "abab6-chat"],
    },
    "deepseek": {
        "name": "DeepSeek",
        "regex": [r"deepseek"],
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "models": ["deepseek-chat", "deepseek-coder"],
    },
    "openai": {
        "name": "OpenAI",
        "regex": [r"api\.openai\.com", r"openai"],
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "siliconflow": {
        "name": "硅基流动",
        "regex": [r"siliconflow", r" SiliconFlow"],
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "Qwen/Qwen2.5-7B-Instruct",
        "models": [
            "Qwen/Qwen2.5-7B-Instruct",
            "Qwen/Qwen2.5-14B-Instruct",
            "deepseek-ai/DeepSeek-V2.5",
            "THUDM/glm-4-9b-chat",
        ],
    },
    "groq": {
        "name": "Groq",
        "regex": [r"groq"],
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-8b-instant",
        "models": ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
    },
    "zhipu": {
        "name": "智谱 AI",
        "regex": [r"zhipu", r"bigmodel\.cn", r"chatglm"],
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-flash",
        "models": ["glm-4-flash", "glm-4", "glm-4-plus", "glm-3-turbo"],
    },
    "dashscope": {
        "name": "阿里云 DashScope",
        "regex": [r"dashscope", r"aliyun", r"modelscope"],
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-turbo",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-long"],
    },
    "baidu": {
        "name": "百度千帆",
        "regex": [r"baidu", r"qianfan", r"wenxin"],
        "base_url": "https://qianfan.baidubce.com/v2/chat/completions",
        "default_model": "ernie-4.0-8k",
        "models": ["ernie-4.0-8k", "ernie-4.0-8k-preview", "ernie-3.5-8k"],
    },
    "spark": {
        "name": "讯飞星火",
        "regex": [r"xfyun", r"spark", r"xinghuo"],
        "base_url": "https://spark-api.xf-yun.com/v3.5/chat",
        "default_model": "v3.5",
        "models": ["v3.5", "v3.0", "v2.0", "v1.5"],
    },
    "ollama": {
        "name": "Ollama (本地)",
        "regex": [r"ollama", r"localhost:11434"],
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2",
        "models": ["llama3.2", "llama3.1", "mistral", "qwen2.5"],
    },
    "custom": {
        "name": "自定义",
        "regex": [],
        "base_url": "",
        "default_model": "",
        "models": [],
    },
}

# ─────────────────────────────────────────────────────────────
# 天气 API 预设
# ─────────────────────────────────────────────────────────────
WEATHER_PRESETS = {
    "openweathermap": {
        "name": "OpenWeatherMap",
        "need_key": True,
        "key_env": "OPENWEATHER_API_KEY",
    },
    "weatherapi": {
        "name": "WeatherAPI.com",
        "need_key": True,
        "key_env": "WEATHERAPI_KEY",
    },
    "qweather": {
        "name": "和风天气",
        "need_key": True,
        "key_env": "QWEATHER_KEY",
    },
    "free": {
        "name": "免费 API (Open-Meteo)",
        "need_key": False,
        "key_env": None,
    },
}

# ─────────────────────────────────────────────────────────────
# 配置文件路径
# ─────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.expanduser("~/.openharness_agent_config.json")

# 配置流程返回上一步的标记
STEP_BACK = "0"


# ─────────────────────────────────────────────────────────────
# 配置持久化
# ─────────────────────────────────────────────────────────────
def load_config() -> dict:
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_config(cfg: dict):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass
