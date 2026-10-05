#!/usr/bin/env python3
"""
Minimal OpenHarness-Style Agent Loop - ver0.3
- 单文件: agent.py
- AI 模型：用户自由选择
- 天气 API：用户自由选择
- 支持真实天气查询
- 分层记忆系统：自动摘要 + 文档检索
"""

import os
import sys
import json
import re
import time
import urllib.request
import urllib.parse
from openai import OpenAI

# ─────────────────────────────────────────────────────────────
# 分层记忆系统
# ─────────────────────────────────────────────────────────────
class Memory:
    """分层记忆系统：关键信息提取 + 定时摘要 + 文档检索"""

    def __init__(self, memory_dir: str = None):
        if memory_dir is None:
            memory_dir = os.path.expanduser("~/.openharness_agent_memory")
        self.memory_dir = memory_dir
        os.makedirs(self.memory_dir, exist_ok=True)

        self.current_summary = []  # 当前积累的对话
        self.summaries = []       # 已生成的摘要列表
        self.message_count = 0     # 消息计数器
        self.SUMMARY_THRESHOLD = 5  # 每5句话生成摘要

        self.summary_file = os.path.join(self.memory_dir, "summaries.json")

        # 每次初始化时清空之前的记忆（新对话开始）
        self.clear_all()

    def clear_all(self):
        """清空所有记忆文件和摘要"""
        try:
            # 删除所有摘要文档
            for f in os.listdir(self.memory_dir):
                if f.startswith("summary_") and f.endswith(".txt"):
                    os.remove(os.path.join(self.memory_dir, f))
            # 清空摘要索引
            self.summaries = []
            self.save_summaries()
            # 清空当前积累
            self.current_summary = []
            self.message_count = 0
        except Exception:
            pass

    def load_summaries(self):
        """加载已有摘要"""
        if os.path.exists(self.summary_file):
            try:
                with open(self.summary_file, "r") as f:
                    data = json.load(f)
                    self.summaries = data.get("summaries", [])
            except Exception:
                self.summaries = []

    def save_summaries(self):
        """保存摘要列表"""
        try:
            with open(self.summary_file, "w") as f:
                json.dump({"summaries": self.summaries}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_message(self, role: str, content: str):
        """添加消息到当前积累"""
        if role == "user" or role == "assistant":
            self.current_summary.append({
                "role": role,
                "content": content,
                "time": time.time()
            })
            self.message_count += 1

    def should_summarize(self) -> bool:
        """判断是否需要生成摘要"""
        return self.message_count >= self.SUMMARY_THRESHOLD

    def extract_key_info(self, client: OpenAI, model: str) -> str:
        """从当前积累中提取关键信息（由模型完成）"""
        if not self.current_summary:
            return ""

        # 构造提取提示
        messages = [
            {
                "role": "system",
                "content": """你是一个信息提取助手。从对话历史中提取关键信息，生成简洁的摘要。

格式要求：
- 用中文
- 列出关键实体（人名、地点、事件、偏好等）
- 列出已完成的任务或决策
- 列出待处理的问题
- 保持简洁，每条不超过20字

示例输出：
[关键实体] 武汉、北京、DeepSeek
[已完成] 询问了武汉天气
[偏好] 喜欢简洁回答
[待处理] 用户想问明天天气"""
            }
        ]

        # 添加对话历史
        for msg in self.current_summary:
            role = "用户" if msg["role"] == "user" else "助手"
            messages.append({
                "role": "user",
                "content": f"{role}说: {msg['content'][:200]}"
            })

        messages.append({
            "role": "user",
            "content": "请提取上述对话的关键信息："
        })

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[摘要生成失败: {e}]"

    def create_summary_doc(self, content: str) -> str:
        """创建摘要文档"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        doc_name = f"summary_{timestamp}.txt"
        doc_path = os.path.join(self.memory_dir, doc_name)

        # 包含时间范围的摘要内容
        start_time = self.current_summary[0]["time"] if self.current_summary else 0
        end_time = self.current_summary[-1]["time"] if self.current_summary else 0
        time_range = f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(start_time))} ~ {time.strftime('%H:%M', time.localtime(end_time))}"

        summary_content = f"""# 对话摘要 {time_range}

## 关键信息
{content}

## 原始对话
"""
        for msg in self.current_summary:
            role = "用户" if msg["role"] == "user" else "助手"
            summary_content += f"\n[{role}] {msg['content'][:100]}..."

        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(summary_content)

        return doc_name

    def summarize(self, client: OpenAI, model: str) -> str:
        """执行摘要：提取信息 + 保存文档"""
        key_info = self.extract_key_info(client, model)
        doc_name = self.create_summary_doc(key_info)

        # 保存摘要索引
        self.summaries.append({
            "doc": doc_name,
            "time": time.time(),
            "preview": key_info[:100] if key_info else ""
        })
        self.save_summaries()

        # 清空当前积累
        self.current_summary = []
        self.message_count = 0

        return doc_name

    def retrieve(self, query: str = "", top_k: int = 5) -> str:
        """检索所有记忆上下文，按时间顺序读取"""
        contexts = []

        # 1. 当前积累的对话（未生成摘要的）
        if self.current_summary:
            current_msgs = []
            for msg in self.current_summary:
                role = "用户" if msg["role"] == "user" else "助手"
                current_msgs.append(f"{role}: {msg['content'][:150]}")
            contexts.append(("current", 0, "【当前对话（未保存）】\n" + "\n".join(current_msgs)))

        # 2. 读取所有已保存的摘要文档，按时间顺序
        all_docs = sorted(self.summaries, key=lambda x: x.get("time", 0))
        for s in all_docs[-top_k:]:  # 取最近 top_k 个
            doc_path = os.path.join(self.memory_dir, s.get("doc", ""))
            if os.path.exists(doc_path):
                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # 提取关键信息和时间
                        time_str = s.get("time", 0)
                        if time_str:
                            time_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(time_str))
                        else:
                            time_str = "未知时间"

                        if "## 关键信息" in content:
                            key_info = content.split("## 关键信息")[1].split("##")[0].strip()
                            contexts.append((s.get("doc", ""), time_str, f"【历史摘要 {time_str}】\n{key_info}"))
                        else:
                            contexts.append((s.get("doc", ""), time_str, f"【历史摘要 {time_str}】\n{content[:200]}"))
                except Exception:
                    pass

        if not contexts:
            return ""

        # 按时间顺序输出
        result_parts = ["\n[完整历史上下文 - 按时间顺序]"]
        for _, _, ctx in contexts:
            result_parts.append(f"\n{ctx}")
        result_parts.append("\n[/完整历史上下文]\n")

        return "".join(result_parts)

    def get_full_context(self) -> str:
        """获取完整上下文（用于工具调用前的思考）"""
        return self.retrieve(top_k=10)

    def reset(self):
        """重置记忆"""
        self.current_summary = []
        self.message_count = 0


# ─────────────────────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────────────────────
config = {}
memory = None

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

# ─────────────────────────────────────────────────────────────
# 工具定义
# ─────────────────────────────────────────────────────────────
def get_tools(weather_provider: str = None):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "计算数学表达式并返回结果",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "数学表达式，如 2 + 2, sqrt(16), 10 * 5"}
                    },
                    "required": ["expression"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_memory",
                "description": "搜索记忆库，获取完整的对话历史上下文。在你需要回答用户问题前，必须先调用此工具了解之前的对话内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词，如用户提到的地点、话题等。不填则返回所有历史"}
                    }
                }
            }
        }
    ]

    if weather_provider:
        tools.append({
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取城市当前天气，包括温度、天气状况、风速等。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "城市名称，如 Beijing, Shanghai, Wuhan, Tokyo"}
                    },
                    "required": ["location"]
                }
            }
        })

        # 添加更换天气 API 的工具
        tools.append({
            "type": "function",
            "function": {
                "name": "change_weather_api",
                "description": "更换天气 API 提供商。当当前 API 无法查询或查询失败时使用。更换前会询问用户确认。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider": {
                            "type": "string",
                            "description": "天气 API 提供商名称",
                            "enum": ["openweathermap", "weatherapi", "qweather", "free"]
                        },
                        "reason": {"type": "string", "description": "更换原因"}
                    },
                    "required": ["provider", "reason"]
                }
            }
        })

    return tools

# ─────────────────────────────────────────────────────────────
# 工具实现
# ─────────────────────────────────────────────────────────────
def calculator(expression: str) -> str:
    try:
        allowed_chars = set("0123456789.+-*/() **%")
        if all(c in allowed_chars or c.isspace() for c in expression):
            result = eval(expression)
            return str(result)
        else:
            return f"错误: 表达式包含无效字符"
    except Exception as e:
        return f"错误: {e}"

def get_weather(city: str, provider: str = None, api_key: str = None) -> str:
    global config

    if provider is None:
        provider = config.get("weather_provider", "free")
    if api_key is None:
        api_key = config.get("weather_api_key", "")

    try:
        encoded_city = urllib.parse.quote(city)

        if provider == "openweathermap":
            if not api_key:
                return "错误: 未配置 OpenWeatherMap API Key"
            url = f"https://api.openweathermap.org/data/2.5/weather?q={encoded_city}&appid={api_key}&units=metric"
            response = urllib.request.urlopen(url, timeout=10)
            data = json.loads(response.read().decode())
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"{data['name']}: {desc}, 温度 {temp}°C"

        elif provider == "weatherapi":
            if not api_key:
                return "错误: 未配置 WeatherAPI Key"
            url = f"https://api.weatherapi.com/v1/current.json?key={api_key}&q={encoded_city}"
            response = urllib.request.urlopen(url, timeout=10)
            data = json.loads(response.read().decode())
            temp = data["current"]["temp_c"]
            desc = data["current"]["condition"]["text"]
            return f"{data['location']['name']}: {desc}, 温度 {temp}°C"

        elif provider == "qweather":
            if not api_key:
                return "错误: 未配置和风天气 API Key"
            geo_url = f"https://geoapi.qweather.com/v2/city/lookup?location={encoded_city}&key={api_key}"
            geo_response = urllib.request.urlopen(geo_url, timeout=10)
            geo_data = json.loads(geo_response.read().decode())
            if not geo_data.get("location"):
                return f"未找到城市: {city}"
            location_id = geo_data["location"][0]["id"]
            weather_url = f"https://devapi.qweather.com/v7/weather/now?location={location_id}&key={api_key}"
            weather_response = urllib.request.urlopen(weather_url, timeout=10)
            weather_data = json.loads(weather_response.read().decode())
            now = weather_data["now"]
            return f"{geo_data['location'][0]['name']}: {now['text']}, 温度 {now['temp']}°C"

        else:  # free / Open-Meteo
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=5"
            geo_response = urllib.request.urlopen(geo_url, timeout=10)
            geo_data = json.loads(geo_response.read().decode())
            if not geo_data.get("results"):
                return f"未找到城市: {city}"

            locations = geo_data["results"]
            # 如果只有一个结果，直接使用
            if len(locations) == 1:
                location = locations[0]
            else:
                # 多个结果：优先选择中国的城市，按人口排序
                china_locs = [loc for loc in locations if loc.get("country_code") == "CN"]
                if china_locs:
                    china_locs.sort(key=lambda x: x.get("population", 0), reverse=True)
                    location = china_locs[0]
                else:
                    # 没有中国城市，选择人口最多的
                    locations.sort(key=lambda x: x.get("population", 0), reverse=True)
                    location = locations[0]

            lat, lon = location["latitude"], location["longitude"]
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m&timezone=auto"
            weather_response = urllib.request.urlopen(weather_url, timeout=10)
            weather_data = json.loads(weather_response.read().decode())
            current = weather_data["current"]
            temp = current["temperature_2m"]
            wind = current["wind_speed_10m"]
            code = current["weather_code"]
            weather_map = {
                0: "☀️ 晴", 1: "🌤️ 晴间多云", 2: "⛅ 多云", 3: "☁️ 阴",
                45: "🌫️ 雾", 48: "🌫️ 雾凇",
                51: "🌦️ 小雨", 53: "🌦️ 中雨", 55: "🌧️ 大雨",
                61: "🌧️ 小雨", 63: "🌧️ 中雨", 65: "🌧️ 大雨",
                71: "🌨️ 小雪", 73: "🌨️ 中雪", 75: "❄️ 大雪",
                80: "🌦️ 阵雨", 81: "🌧️ 中阵雨", 82: "⛈️ 强阵雨",
                95: "⛈️ 雷暴", 96: "⛈️ 雷暴冰雹", 99: "⛈️ 强雷暴",
            }
            desc = weather_map.get(code, f"代码{code}")
            return f"{location['name']}: {desc}, 温度 {temp}°C, 风速 {wind} km/h"

    except Exception as e:
        return f"查询天气失败: {e}"

def change_weather_api(provider: str, reason: str = "") -> str:
    """更换天气 API 提供商"""
    global config

    provider_names = {
        "openweathermap": "OpenWeatherMap",
        "weatherapi": "WeatherAPI.com",
        "qweather": "和风天气",
        "free": "免费 API (Open-Meteo)"
    }

    provider_name = provider_names.get(provider, provider)

    # 打印询问确认
    print(f"\n{'='*50}")
    print(f"🤖 Agent 请求更换天气 API")
    print(f"   当前: {WEATHER_PRESETS.get(config.get('weather_provider', 'free'), {}).get('name', '未知')}")
    print(f"   更换为: {provider_name}")
    print(f"   原因: {reason}")
    print(f"{'='*50}")
    confirm = input("Allow? (y/n): ").strip().lower()

    if confirm == "y":
        config["weather_provider"] = provider
        save_config(config)
        return f"✅ 已更换天气 API 为 {provider_name}"
    else:
        return f"❌ 用户拒绝了更换请求"

def get_tool_impls(weather_provider: str = None):
    global memory
    impls = {
        "calculator": calculator,
        "search_memory": lambda query="": memory.retrieve(query) if memory else "记忆系统未初始化",
        "change_weather_api": change_weather_api,
    }
    if weather_provider:
        impls["get_weather"] = lambda city, p=weather_provider: get_weather(city, p)
    return impls

# ─────────────────────────────────────────────────────────────
# 消息历史
# ─────────────────────────────────────────────────────────────
def create_messages(weather_provider: str = None, memory_context: str = ""):
    weather_info = ""
    if weather_provider and weather_provider != "free":
        weather_info = """
当你需要查询天气信息时（如用户问"北京天气怎么样"、"武汉热不热"、"今天适合穿什么"等），你必须调用 get_weather 工具。
不要假设或编造天气数据，必须先调用工具获取真实数据。
根据天气数据回答用户的问题。"""

    return [
        {
            "role": "system",
            "content": f"""你叫小小泽，是一个智能 AI 助手。

{memory_context}

【关键规则 - 必须遵守】
在回答用户任何问题之前，你必须先调用 search_memory 工具获取完整的历史上下文！
这是强制要求，不是可选项。

【重要】工具调用后的行为：
- 获取到工具返回结果后，不要只复述结果就结束！
- 必须结合所有工具返回的信息，给出完整、详细的回答
- 例如：获取天气数据后，必须给出穿衣建议、温度感受、活动建议等完整内容
- 直到完成全部回答后才能输出，不要在中间过程就停止

【上下文记忆使用规则】
- 先调用 search_memory 获取用户之前的对话记录
- 如果返回的上下文中有提到某个城市、地点或话题，基于这些信息回答
- 用户说"明天呢"、"那XX呢"、"继续"、"还有呢"等指代词时，必须从历史上下文中推断
- 例如：历史中说"武汉：☀️ 晴"，用户问"明天呢" → 调用 get_weather(location="Wuhan")
- 如果上下文中有城市信息，直接使用；没有的话才询问用户

可用工具：
1. search_memory - 必用！回答前先调用获取完整历史上下文
2. calculator - 当用户需要计算数学表达式时使用
3. get_weather - 当用户询问天气、需要穿衣建议、想知道某地温度等天气相关问题时使用
4. change_weather_api - 更换天气 API 提供商（当 get_weather 查询失败时使用）

【天气工具使用】
- get_weather 只接受英文城市名！
- 北京 → Beijing, 武汉 → Wuhan, 上海 → Shanghai
- 先翻译成英文再调用
- 注意：一些城市名有歧义，如"Yichun"可能是江西宜春或黑龙江伊春
  - 如果用户只说"伊春"而不指定省份，先询问确认
  - 如果上下文能推断出省份，使用省份+城市名，如 "Heilongjiang"

【更换天气 API】
- 当 get_weather 返回"未找到城市"或"查询失败"时，可以调用 change_weather_api 更换其他 API
- 可选 provider: "openweathermap", "weatherapi", "qweather", "free"
- 更换前会询问用户确认

使用规则：
- 回答前必须先 search_memory
- 天气问题必须先翻译成英文城市名，再调用 get_weather
- 天气查询失败时，尝试更换 API
- 获取工具结果后，必须给出完整回答，不能只复述结果就结束
{weather_info}

保持回答简洁、有帮助。"""
        }
    ]

# ─────────────────────────────────────────────────────────────
# API 自动识别
# ─────────────────────────────────────────────────────────────
def detect_provider(base_url: str) -> tuple:
    base_url_lower = base_url.lower()
    for key, preset in MODEL_PRESETS.items():
        for pattern in preset["regex"]:
            if re.search(pattern, base_url_lower):
                return key, preset
    return "custom", MODEL_PRESETS["custom"]

# ─────────────────────────────────────────────────────────────
# 分步配置
# ─────────────────────────────────────────────────────────────
STEP_BACK = "0"

def step1_select_input_method() -> str:
    print("\n" + "=" * 50)
    print("🤖 OpenHarness Agent - ver0.3")
    print("=" * 50)
    print("\n请选择 AI API 输入方式:")
    print("  1. 我有 API 端点（自动识别提供商）")
    print("  2. 我有 API Key（自动识别）")
    print("  3. 从预设列表选择")

    while True:
        choice = input(f"\n选择 (1-3) [{STEP_BACK} 返回]: ").strip()
        if choice == STEP_BACK:
            print("已是第一步，无法返回")
            continue
        if choice in ("1", "2", "3"):
            return choice
        print("无效选择，请输入 1、2、3")

def step2_input_base_url(state: dict) -> dict:
    print("\n" + "-" * 40)
    print("📍 输入 AI API 端点")
    print(f"   输入 {STEP_BACK} 返回")

    while True:
        base_url = input("\nAPI 端点: ").strip()
        if base_url == STEP_BACK:
            return None
        if base_url:
            provider_key, preset = detect_provider(base_url)
            print(f"\n🔍 自动识别: {preset['name']}")
            state["base_url"] = base_url
            state["provider_key"] = provider_key
            state["preset"] = preset
            return state
        print("端点不能为空")

def step2_input_api_key(state: dict) -> dict:
    print("\n" + "-" * 40)
    print("📍 输入 AI API Key")
    print(f"   输入 {STEP_BACK} 返回")

    while True:
        api_key = input("\nAPI Key: ").strip()
        if api_key == STEP_BACK:
            return None
        if api_key:
            if api_key.startswith("sk-"):
                base_url = "https://api.openai.com/v1"
            elif len(api_key) == 32 and api_key.isalnum():
                base_url = "https://api.deepseek.com/v1"
            else:
                base_url = input("\n无法识别，请输入 API 端点: ").strip()
                if base_url == STEP_BACK:
                    continue
            if not base_url.endswith("/v1"):
                base_url = base_url.rstrip("/") + "/v1"
            provider_key, preset = detect_provider(base_url)
            print(f"\n🔍 自动识别: {preset['name']}")
            state["api_key"] = api_key
            state["base_url"] = base_url
            state["provider_key"] = provider_key
            state["preset"] = preset
            return state
        print("Key 不能为空")

def step2_select_from_preset(state: dict) -> dict:
    print("\n" + "-" * 40)
    print("📍 选择 AI 模型提供商")
    print(f"   输入 {STEP_BACK} 返回\n")

    preset_list = [(k, v) for k, v in MODEL_PRESETS.items() if k != "custom"]
    for i, (key, p) in enumerate(preset_list, 1):
        models_str = ", ".join(p["models"][:2])
        if len(p["models"]) > 2:
            models_str += "..."
        print(f"  {i}. {p['name']}")
        print(f"     模型: {models_str}")

    while True:
        c = input(f"\n选择 (1-{len(preset_list)}) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None
        if c.isdigit() and 1 <= int(c) <= len(preset_list):
            provider_key, preset = preset_list[int(c) - 1]
            state["provider_key"] = provider_key
            state["preset"] = preset
            state["base_url"] = preset["base_url"]
            return state
        print(f"无效选择")

def step3_input_api_key(state: dict) -> dict:
    print("\n" + "-" * 40)
    print(f"📍 输入 {state['preset']['name']} API Key")
    print(f"   输入 {STEP_BACK} 返回")

    preset = state["preset"]
    env_var = f"{preset['name'].upper().replace(' ', '_')}_API_KEY"
    env_key = os.environ.get(env_var)
    if not env_key:
        env_key = os.environ.get("OPENAI_API_KEY")
    if env_key:
        print(f"\n   检测到环境变量，自动使用")
        state["api_key"] = env_key
        return state

    while True:
        api_key = input("\nAPI Key: ").strip()
        if api_key == STEP_BACK:
            return None
        if api_key:
            state["api_key"] = api_key
            return state
        print("Key 不能为空")

def step4_select_model(state: dict) -> dict:
    print("\n" + "-" * 40)
    print(f"📍 选择 {state['preset']['name']} 模型")
    print(f"   输入 {STEP_BACK} 返回\n")

    preset = state["preset"]
    for i, m in enumerate(preset["models"], 1):
        default_mark = " (默认)" if m == preset["default_model"] else ""
        print(f"  {i}. {m}{default_mark}")
    print(f"  c. 自定义（输入任意模型名称）")

    while True:
        c = input(f"\n选择模型 (1-{len(preset['models'])}, c 自定义) [{STEP_BACK} 返回]: ").strip().lower()
        if c == STEP_BACK:
            return None
        if c == "c":
            model = input("请输入自定义模型名称: ").strip()
            if model and model != STEP_BACK:
                state["model"] = model
                return state
            continue
        if c.isdigit() and 1 <= int(c) <= len(preset["models"]):
            state["model"] = preset["models"][int(c) - 1]
            return state
        if c in preset["models"]:
            state["model"] = c
            return state
        print(f"无效选择")

def step5_select_weather_provider(state: dict) -> dict:
    print("\n" + "-" * 40)
    print("📍 选择天气 API 提供商")
    print(f"   输入 {STEP_BACK} 返回\n")

    for i, (key, p) in enumerate(WEATHER_PRESETS.items(), 1):
        need_key = "(需要 API Key)" if p["need_key"] else "(免费，无需 Key)"
        print(f"  {i}. {p['name']} {need_key}")

    preset_list = list(WEATHER_PRESETS.items())

    while True:
        c = input(f"\n选择 (1-{len(preset_list)}) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None
        if c.isdigit() and 1 <= int(c) <= len(preset_list):
            weather_key, weather_preset = preset_list[int(c) - 1]
            state["weather_provider"] = weather_key
            state["weather_preset"] = weather_preset
            return state
        print(f"无效选择")

def step6_input_weather_key(state: dict) -> dict:
    weather_preset = state.get("weather_preset", {})

    if not weather_preset.get("need_key"):
        state["weather_api_key"] = ""
        return state

    print("\n" + "-" * 40)
    print(f"📍 输入 {weather_preset['name']} API Key")
    print(f"   输入 {STEP_BACK} 返回")

    key_env = weather_preset.get("key_env")
    if key_env:
        env_key = os.environ.get(key_env)
        if env_key:
            print(f"\n   检测到环境变量，自动使用")
            state["weather_api_key"] = env_key
            return state

    while True:
        api_key = input("\nAPI Key: ").strip()
        if api_key == STEP_BACK:
            return None
        if api_key:
            state["weather_api_key"] = api_key
            return state
        print("Key 不能为空")

def get_config(force_reset: bool = False):
    global config

    if not force_reset:
        saved = load_config()
        if saved.get("api_key") and saved.get("base_url") and saved.get("model"):
            print("\n" + "=" * 50)
            print("🤖 小小泽 - ver0.3")
            print("=" * 50)
            print(f"\n📌 检测到已保存的配置:")
            print(f"   AI 提供商: {saved.get('provider', '未知')}")
            print(f"   AI 模型: {saved.get('model')}")
            weather_provider = saved.get("weather_provider", "free")
            weather_name = WEATHER_PRESETS.get(weather_provider, {}).get("name", "未知")
            print(f"   天气 API: {weather_name}")
            print(f"\n   输入 'api choose' 可重新选择配置")

            config = saved
            return saved

    state = {}

    input_method = step1_select_input_method()
    if input_method == "1":
        result = step2_input_base_url(state)
        if result is None:
            return get_config()
    elif input_method == "2":
        result = step2_input_api_key(state)
        if result is None:
            return get_config()
    else:
        result = step2_select_from_preset(state)
        if result is None:
            return get_config()

    result = step3_input_api_key(state)
    if result is None:
        return get_config()

    result = step4_select_model(state)
    if result is None:
        return get_config()

    result = step5_select_weather_provider(state)
    if result is None:
        return get_config()

    result = step6_input_weather_key(state)
    if result is None:
        return get_config()

    base_url = state["base_url"]
    if base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    cfg = {
        "base_url": base_url,
        "api_key": state["api_key"],
        "model": state["model"],
        "provider": state["preset"]["name"],
        "provider_key": state["provider_key"],
        "weather_provider": state["weather_provider"],
        "weather_api_key": state.get("weather_api_key", ""),
    }

    save_config(cfg)
    config = cfg

    print("\n" + "=" * 50)
    print("✅ 配置完成并已保存!")
    print(f"   AI 提供商: {state['preset']['name']}")
    print(f"   AI 模型: {state['model']}")
    print(f"   天气 API: {state['weather_preset']['name']}")
    print("=" * 50)

    return cfg

# ─────────────────────────────────────────────────────────────
# 工具调用处理
# ─────────────────────────────────────────────────────────────
def execute_tool_calls(messages: list, tools: list, tool_impls: dict, client: OpenAI, model: str) -> bool:
    """
    执行工具调用循环，直到模型给出文字回答
    返回 True 表示对话继续，False 表示结束
    """
    while True:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.7,
                max_tokens=4000,  # 限制最大输出
            )
            assistant_msg = response.choices[0].message

            # 优先处理 tool_calls
            if assistant_msg.tool_calls:
                # 模型请求调用工具
                for tool_call in assistant_msg.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    print(f"\n🔧 调用工具: {tool_name}({tool_args})")

                    if tool_name in tool_impls:
                        if tool_name == "get_weather":
                            result = tool_impls[tool_name](tool_args.get("location", ""))
                        else:
                            result = tool_impls[tool_name](**tool_args)
                    else:
                        result = f"错误: 未知工具 {tool_name}"

                    result_preview = result[:100] + "..." if len(result) > 100 else result
                    print(f"   → {result_preview}")

                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": result
                    })

                # 继续循环，让模型分析工具结果并决定下一步
                continue

            elif assistant_msg.content:
                # 检查是否因达到限制而被截断
                finish_reason = response.choices[0].finish_reason
                if finish_reason == "length":
                    print(f"\n⚠️ 回答被截断（达到 token 限制），继续...")
                    # 追加截断提示，让模型继续
                    messages.append({"role": "assistant", "content": assistant_msg.content})
                    messages.append({
                        "role": "user",
                        "content": "请继续完成你的回答，不要重复之前的内容，直接继续。"
                    })
                    continue

                print(f"\n小小泽: {assistant_msg.content}")
                messages.append({"role": "assistant", "content": assistant_msg.content})
                return True

        except Exception as e:
            print(f"\n❌ 工具调用错误: {e}")
            return True

# ─────────────────────────────────────────────────────────────
# Agent 主循环
# ─────────────────────────────────────────────────────────────
def run_loop(client: OpenAI, model: str, provider: str, weather_provider: str):
    global memory

    # 初始化记忆系统
    memory = Memory()

    tools = get_tools(weather_provider)
    tool_impls = get_tool_impls(weather_provider)

    # 初始消息（不带记忆上下文）
    messages = create_messages(weather_provider, "")

    print("\n" + "=" * 50)
    print("🤖 小小泽 运行中")
    print(f"   AI: {provider} / {model}")
    print(f"   天气: {WEATHER_PRESETS.get(weather_provider, {}).get('name', '未知')}")
    print("   输入 'quit' 退出，Ctrl+C 随时退出")
    print("   输入 'clear' 清空对话")
    print("   输入 'api choose' 重新选择配置")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except KeyboardInterrupt:
            print("\n\n再见!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见!")
            break

        if user_input.lower() == "clear":
            memory.reset()
            messages = create_messages(weather_provider, "")
            print("✅ 对话已清空，记忆已重置")
            continue

        if user_input.lower() == "api choose":
            print("\n📌 正在重新选择配置...")
            return "reconfigure"

        if not user_input:
            continue

        # 检查是否需要生成摘要（每5条消息）
        if memory.should_summarize():
            print("\n📝 正在生成对话摘要...")
            doc_name = memory.summarize(client, model)
            print(f"   摘要已保存: {doc_name}")

        # 添加用户消息到历史
        messages.append({"role": "user", "content": user_input})

        # 自动注入记忆上下文
        memory_context = memory.retrieve()
        if memory_context:
            # 在用户消息后插入记忆上下文
            user_msg = messages[-1]
            messages[-1] = {"role": "user", "content": f"{user_msg['content']}\n\n{memory_context}"}

        # 调用工具处理循环（持续调用直到模型给出最终回答）
        try:
            execute_tool_calls(messages, tools, tool_impls, client, model)
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            messages.pop()  # 移除失败的用户消息
            continue

# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────
def main():
    global config, memory

    config = get_config()

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    while True:
        result = run_loop(
            client,
            config["model"],
            config["provider"],
            config.get("weather_provider", "free")
        )

        if result == "reconfigure":
            config = get_config(force_reset=True)
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
            )
            continue

        break

if __name__ == "__main__":
    main()
