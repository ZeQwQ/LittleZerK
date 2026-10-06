#!/usr/bin/env python3
"""
Minimal OpenHarness-Style Agent Loop - ver0.4
- 单文件: agent.py
- AI 模型：用户自由选择
- 天气 API：用户自由选择
- 支持真实天气查询
- 分层记忆系统：自动摘要 + 文档检索
- ToDoList 工具：工作前必须先创建任务清单
- 联网搜索：机票、火车票、网页搜索
- 本地文件读取：PDF、Markdown、txt
"""

import os
import sys
import json
import re
import time
import ast
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
        self.SUMMARY_THRESHOLD = 10  # 每10句话生成摘要（减少频繁压缩）

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

        # 构造提取提示 - 紧凑格式
        messages = [
            {
                "role": "system",
                "content": """你是一个信息提取助手。从对话历史中提取关键信息，生成极简摘要。

格式要求（严格按此格式）：
K:关键信息1|关键信息2|关键信息3...
A:已完成的任务或结论
P:待处理的问题或用户的下一步意图

规则：
- K行：列出关键实体、已完成查询、获取到的数据等，每个用|分隔
- A行：当前任务是否完成，完成了写结论，未完成写进行中
- P行：用户可能的下一步意图，或助手接下来要做什么
- 总字数控制在150字以内
- 直接输出，不要加任何标记符号（如##、###等）

正确示例：
K:用户问北京和上海的天气对比|助手查了北京晴22C|助手查了上海多云19C|助手对比了两地温度差异|助手给出了出行建议(上海需带伞)
A:完成天气查询和对比分析|已给出完整回答
P:任务完成，等待用户下一个问题

错误示例（不要这样写）：
[关键实体] 北京、上海
[已完成] 天气查询
[待处理] 无"""
            }
        ]

        # 添加对话历史（限制长度减少token）
        for msg in self.current_summary:
            role = "用户" if msg["role"] == "user" else "助手"
            # 限制每条消息长度
            content = msg['content'][:300] if len(msg['content']) > 300 else msg['content']
            messages.append({
                "role": "user",
                "content": f"{role}: {content}"
            })

        messages.append({
            "role": "user",
            "content": "请提取关键信息（严格按K:|A:|P:格式）："
        })

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
                max_tokens=300,  # 减少token
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[摘要失败: {e}]"

    def create_summary_doc(self, content: str) -> str:
        """创建摘要文档 - 极简格式"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        doc_name = f"summary_{timestamp}.txt"
        doc_path = os.path.join(self.memory_dir, doc_name)

        # 获取时间范围
        start_time = self.current_summary[0]["time"] if self.current_summary else 0
        end_time = self.current_summary[-1]["time"] if self.current_summary else 0
        time_str = time.strftime("%m-%d %H:%M", time.localtime(start_time))

        # 极简格式：时间 + 摘要内容
        summary_content = f"## {time_str}\n{content}"

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

    def retrieve(self, query: str = "") -> str:
        """
        检索记忆上下文，动态决定看多少摘要和当前积累

        规则：
        - 每 10 条消息生成一个摘要
        - message_count = 1-9: 看 0 个摘要 + 1-9 条当前积累
        - message_count = 10: 看 1 个摘要 + 0 条积累（刚生成摘要）
        - message_count = 11-19: 看 1 个摘要 + 1-9 条当前积累
        - message_count = 20: 看 2 个摘要 + 0 条积累（刚生成摘要）
        - message_count = 21-29: 看 2 个摘要 + 1-9 条当前积累
        - 以此类推...
        """
        contexts = []

        # 计算看几个摘要和当前积累
        if self.message_count == 0:
            # 刚生成摘要，没有当前积累
            visible_summaries = len(self.summaries)
            current_msgs = []
        elif self.message_count % 10 == 0:
            # 刚好是 10 的倍数，刚生成摘要，只看对应数量摘要
            visible_summaries = self.message_count // 10
            current_msgs = []
        else:
            # 还有当前积累没保存
            visible_summaries = self.message_count // 10
            if self.current_summary:
                current_msgs = []
                for msg in self.current_summary:
                    role = "用户" if msg["role"] == "user" else "助手"
                    current_msgs.append(f"{role}: {msg['content'][:100]}")

        # 1. 当前积累的对话（如果有）
        if current_msgs:
            contexts.append(("current", 0, "".join(current_msgs)))

        # 2. 读取对应数量的已保存摘要文档，按时间顺序
        all_docs = sorted(self.summaries, key=lambda x: x.get("time", 0))
        for s in all_docs[-visible_summaries:]:
            doc_path = os.path.join(self.memory_dir, s.get("doc", ""))
            if os.path.exists(doc_path):
                try:
                    with open(doc_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # 提取时间
                        time_str = s.get("time", 0)
                        if time_str:
                            time_str = time.strftime("%m-%d %H:%M", time.localtime(time_str))
                        else:
                            time_str = "??-??"

                        # 新格式：K:|A:|P:，直接读取
                        if "K:" in content or "A:" in content or "P:" in content:
                            lines = content.strip().split('\n')
                            if lines and lines[0].startswith('## '):
                                summary_content = '\n'.join(lines[1:])
                            else:
                                summary_content = content
                            contexts.append((s.get("doc", ""), time_str, f"[{time_str}]\n{summary_content}"))
                        else:
                            contexts.append((s.get("doc", ""), time_str, f"[{time_str}]\n{content[:100]}"))
                except Exception:
                    pass

        if not contexts:
            return ""

        # 紧凑格式输出
        result_parts = ["\n[历史"]
        for _, time_str, ctx in contexts:
            result_parts.append(f"\n{ctx}")
        result_parts.append("\n]\n")

        return "".join(result_parts)

    def get_full_context(self) -> str:
        """获取完整上下文（用于工具调用前的思考）"""
        return self.retrieve()

    def reset(self):
        """重置记忆"""
        self.current_summary = []
        self.message_count = 0


# ─────────────────────────────────────────────────────────────
# 全局配置
# ─────────────────────────────────────────────────────────────
config = {}
memory = None
todo_list = None  # ToDoList 实例

# ─────────────────────────────────────────────────────────────
# ToDoList 任务清单系统
# ─────────────────────────────────────────────────────────────
class ToDoList:
    """任务清单：工作前必须创建任务清单，一步一步执行"""

    def __init__(self):
        self.tasks = []       # 任务列表
        self.completed = []   # 已完成任务
        self.current_index = 0  # 当前任务索引
        self.is_active = False  # 清单是否激活

    def create(self, tasks: list[str]) -> str:
        """创建任务清单"""
        if not tasks:
            return "❌ 任务清单不能为空"

        self.tasks = tasks
        self.completed = []
        self.current_index = 0
        self.is_active = True

        # 格式化输出清单
        result = ["✅ 任务清单已创建："]
        for i, task in enumerate(tasks, 1):
            result.append(f"  {i}. {task}")
        result.append(f"\n📋 共 {len(tasks)} 个任务，开始执行...")
        return "\n".join(result)

    def get_current_task(self) -> str | None:
        """获取当前任务"""
        if not self.is_active or self.current_index >= len(self.tasks):
            return None
        return self.tasks[self.current_index]

    def complete_task(self, result: str = "") -> str:
        """标记当前任务完成，返回下一个任务"""
        if not self.is_active:
            return ""

        task = self.get_current_task()
        if task:
            self.completed.append({
                "task": task,
                "result": result,
                "index": self.current_index
            })

        self.current_index += 1

        # 检查是否全部完成
        if self.current_index >= len(self.tasks):
            return "【清单完成】"

        # 返回下一个任务
        next_task = self.tasks[self.current_index]
        return f"【任务 {self.current_index + 1}/{len(self.tasks)}】{next_task}"

    def get_status(self) -> str:
        """获取清单状态"""
        if not self.is_active:
            return "❌ 暂无任务清单"

        status = [f"📋 任务清单状态 ({self.current_index}/{len(self.tasks)} 完成)："]
        for i, task in enumerate(self.tasks):
            if i < self.current_index:
                status.append(f"  ✅ {i+1}. {task}")
            elif i == self.current_index:
                status.append(f"  🔄 {i+1}. {task} (进行中)")
            else:
                status.append(f"  ⏳ {i+1}. {task}")
        return "\n".join(status)

    def is_complete(self) -> bool:
        """检查清单是否全部完成"""
        return self.is_active and self.current_index >= len(self.tasks)

    def reset(self):
        """重置清单"""
        self.tasks = []
        self.completed = []
        self.current_index = 0
        self.is_active = False

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
        },
        {
            "type": "function",
            "function": {
                "name": "create_todo_list",
                "description": "创建任务清单。收到用户问题后，必须先创建清单列出解决步骤，然后按清单逐步执行。清单只保存在内存中。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tasks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "任务步骤列表，如 [\"搜索记忆了解上下文\", \"查询天气\", \"综合回答\"]"
                        }
                    },
                    "required": ["tasks"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "complete_task",
                "description": "标记当前任务完成，系统会返回下一个任务。必须按清单顺序一个一个完成任务。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string", "description": "当前任务的执行结果简述"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_session_state",
                "description": "保存当前会话状态到 latest.json 文件。包括 session_id、配置、todo 状态、记忆状态等。用于会话结束或需要保存进度时调用。",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "获取当前日期和时间。返回格式化的当前时间，包括年、月、日、时、分、秒和星期几。",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_flight",
                "description": "搜索机票信息。输入出发地、目的地和日期，返回航班搜索结果（仅供参考，不支持购票）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departure": {"type": "string", "description": "出发城市，如 Beijing、Peking"},
                        "destination": {"type": "string", "description": "目的城市，如 Shanghai"},
                        "date": {"type": "string", "description": "出发日期，格式 YYYY-MM-DD，如 2026-10-10"}
                    },
                    "required": ["departure", "destination", "date"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_train",
                "description": "搜索火车票信息。输入出发地、目的地，返回火车车次搜索结果（仅供参考，不支持购票）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "departure": {"type": "string", "description": "出发城市，如 Beijing"},
                        "destination": {"type": "string", "description": "目的城市，如 Shanghai"}
                    },
                    "required": ["departure", "destination"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "通用网页搜索。输入任意搜索关键词，返回相关网页结果。适用于新闻、价格、知识百科、餐厅推荐等各种问题。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词/问题，如 Python教程、今日新闻、iPhone价格"}
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "读取本地文件内容。支持 PDF、Markdown、txt 格式，提取文件中的文字内容。读取后可以基于文件内容回答用户问题。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "文件的完整路径，如 /Users/zerk/Documents/笔记.md 或 ./readme.md"}
                    },
                    "required": ["file_path"]
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
    """安全的数学表达式计算器"""
    try:
        allowed_chars = set("0123456789.+-*/() **%")
        if not all(c in allowed_chars or c.isspace() for c in expression):
            return "错误: 表达式包含无效字符"

        # 使用 AST 解析验证表达式语法
        tree = ast.parse(expression, mode='eval')

        # 验证只包含数学运算（禁止函数调用、变量引用等）
        allowed_nodes = (
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
            ast.USub, ast.UAdd
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                return "错误: 表达式包含不支持的操作"

        # 使用受限命名空间安全执行
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
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

def save_session_state(msgs: list = None) -> str:
    """保存当前会话状态"""
    global config, memory, todo_list
    import uuid
    from datetime import datetime

    save_mode = config.get("session_save_mode", "overwrite")

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_id = str(uuid.uuid4())[:8]

        # 提取对话摘要（用户问题和助手回答）
        dialogue_summary = []
        if msgs:
            for m in msgs:
                if m["role"] == "user":
                    content = m.get("content", "")[:100]
                    dialogue_summary.append(f"用户: {content}{'...' if len(m.get('content', '')) > 100 else ''}")
                elif m["role"] == "assistant" and m.get("content"):
                    content = m.get("content", "")[:100]
                    dialogue_summary.append(f"助手: {content}{'...' if len(m.get('content', '')) > 100 else ''}")

        # 提取待完成任务列表
        pending_tasks = []
        if todo_list and todo_list.is_active:
            for i in range(todo_list.current_index, len(todo_list.tasks)):
                pending_tasks.append(todo_list.tasks[i])

        latest_entry = {
            "session_id": session_id,
            "timestamp": timestamp,
            "cwd": os.getcwd(),
            "model": config.get("model", "unknown"),
            "ai_provider": config.get("provider", "unknown"),
            "ai_base_url": config.get("base_url", ""),
            "weather_provider": config.get("weather_provider", "free"),
            "date": timestamp,
            "todo_list": {
                "is_active": todo_list.is_active if todo_list else False,
                "current_index": todo_list.current_index if todo_list else 0,
                "total_tasks": len(todo_list.tasks) if todo_list else 0,
                "completed_tasks": len(todo_list.completed) if todo_list else 0,
                "tasks": todo_list.tasks if todo_list else [],
                "completed_details": [
                    {"task": c["task"], "result": c.get("result", "")[:50]}
                    for c in (todo_list.completed if todo_list else [])
                ],
                "pending_tasks": pending_tasks,
            },
            "memory": {
                "message_count": memory.message_count if memory else 0,
                "summary_count": len(memory.summaries) if memory else 0,
                "summaries_preview": [
                    {"doc": s.get("doc", ""), "preview": s.get("preview", "")[:100]}
                    for s in (memory.summaries[-3:] if memory else [])
                ],
            },
            "message_count": len([m for m in msgs if m["role"] in ("user", "assistant")]),
            "dialogue_summary": dialogue_summary[-10:],  # 最近10条对话
        }

        if save_mode == "timestamp":
            # 时间戳模式：保存为 latest_{timestamp}.json
            filename = f"latest_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(latest_entry, f, ensure_ascii=False, indent=2)

            # 更新 index 文件
            index_file = "latest_index.json"
            try:
                if os.path.exists(index_file):
                    with open(index_file, "r") as f:
                        index_data = json.load(f)
                else:
                    index_data = {"sessions": []}
            except:
                index_data = {"sessions": []}

            index_data["sessions"].insert(0, {
                "session_id": session_id,
                "timestamp": timestamp,
                "filename": filename,
                "model": config.get("model", "unknown"),
                "message_count": latest_entry["message_count"],
                "todo_summary": f"{todo_list.current_index if todo_list else 0}/{len(todo_list.tasks) if todo_list else 0}" if todo_list and todo_list.tasks else "无",
                "dialogue_preview": dialogue_summary[-2:] if dialogue_summary else [],
            })
            index_data["sessions"] = index_data["sessions"][:10]

            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            return f"✅ 会话已保存: {filename}"
        else:
            # 覆盖模式：只保存 latest.json
            with open("latest.json", "w", encoding="utf-8") as f:
                json.dump(latest_entry, f, ensure_ascii=False, indent=2)

            return "✅ 会话已保存: latest.json"

        return f"✅ 会话已保存: {filename}"
    except Exception as e:
        return f"❌ 保存失败: {e}"

def get_current_time() -> str:
    """获取当前日期和时间"""
    from datetime import datetime

    now = datetime.now()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekday_names[now.weekday()]

    return (f"当前时间：{now.strftime('%Y年%m月%d日 %H:%M:%S')}\n"
            f"星期：{weekday}\n"
            f"年份：{now.year}年\n"
            f"月份：{now.month}月\n"
            f"日期：{now.day}日")

def search_flight(departure: str, destination: str, date: str) -> str:
    """搜索机票信息"""
    try:
        import requests
        from bs4 import BeautifulSoup

        query = f"{departure} to {destination} flight {date}"
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []
        for item in soup.select('li.b_algo')[:8]:
            title_elem = item.select_one('h2 a')
            snippet_elem = item.select_one('div.b_caption p')
            if title_elem:
                results.append({
                    "title": title_elem.get_text(),
                    "url": title_elem.get('href', ''),
                    "snippet": snippet_elem.get_text()[:200] if snippet_elem else ''
                })

        if not results:
            return f"未找到 {departure} 到 {destination} 的航班信息"

        output = [f"🔍 航班搜索结果：{departure} → {destination}（{date}）\n"]
        output.append(f"共找到 {len(results)} 条结果（仅供参考，实际价格请以官网为准）：\n")

        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r['title']}")
            output.append(f"   {r['snippet']}")
            output.append(f"   链接：{r['url']}\n")

        return "\n".join(output)
    except Exception as e:
        return f"搜索失败：{e}"

def search_train(departure: str, destination: str) -> str:
    """搜索火车票信息"""
    try:
        import requests
        from bs4 import BeautifulSoup

        query = f"{departure} to {destination} train schedule"
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []
        for item in soup.select('li.b_algo')[:8]:
            title_elem = item.select_one('h2 a')
            snippet_elem = item.select_one('div.b_caption p')
            if title_elem:
                results.append({
                    "title": title_elem.get_text(),
                    "url": title_elem.get('href', ''),
                    "snippet": snippet_elem.get_text()[:200] if snippet_elem else ''
                })

        if not results:
            return f"未找到 {departure} 到 {destination} 的火车信息"

        output = [f"🔍 火车搜索结果：{departure} → {destination}\n"]
        output.append(f"共找到 {len(results)} 条结果（仅供参考，实际信息请以12306官网为准）：\n")

        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r['title']}")
            output.append(f"   {r['snippet']}")
            output.append(f"   链接：{r['url']}\n")

        return "\n".join(output)
    except Exception as e:
        return f"搜索失败：{e}"

def search_web(query: str) -> str:
    """通用网页搜索"""
    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []
        for item in soup.select('li.b_algo')[:6]:
            title_elem = item.select_one('h2 a')
            snippet_elem = item.select_one('div.b_caption p')
            if title_elem:
                results.append({
                    "title": title_elem.get_text(),
                    "url": title_elem.get('href', ''),
                    "snippet": snippet_elem.get_text()[:200] if snippet_elem else ''
                })

        if not results:
            return f"未找到关于「{query}」的相关结果"

        output = [f"🔍 搜索结果：{query}\n"]
        output.append(f"共找到 {len(results)} 条结果：\n")

        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r['title']}")
            output.append(f"   {r['snippet']}")
            output.append(f"   链接：{r['url']}\n")

        return "\n".join(output)
    except Exception as e:
        return f"搜索失败：{e}"

def read_file(file_path: str) -> str:
    """读取本地文件（PDF 或 Markdown），提取主要内容"""
    import os

    # 安全检查：防止路径遍历
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        return f"❌ 文件不存在：{file_path}"

    # 检查文件大小（限制 10MB）
    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:
        return f"❌ 文件太大（{file_size / 1024 / 1024:.1f}MB），请选择 10MB 以内的文件"

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"[第{i+1}页]\n{text}")
            if not text_parts:
                return "⚠️ PDF 中未提取到文字，可能是因为扫描版 PDF"
            content = "\n\n".join(text_parts)
            return f"📄 PDF 文件：{os.path.basename(file_path)}\n共 {len(reader.pages)} 页\n\n{content[:8000]}"
        elif ext == ".md":
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"📝 Markdown 文件：{os.path.basename(file_path)}\n\n{content[:10000]}"
        elif ext in (".txt", ".text"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"📄 文本文件：{os.path.basename(file_path)}\n\n{content[:10000]}"
        else:
            return f"❌ 不支持的文件格式：{ext}，仅支持 .pdf、.md、.txt"
    except Exception as e:
        return f"❌ 读取文件失败：{e}"

def get_tool_impls(weather_provider: str = None):
    global memory, todo_list
    impls = {
        "calculator": calculator,
        "search_memory": lambda query="": memory.retrieve(query) if memory else "记忆系统未初始化",
        "change_weather_api": change_weather_api,
        "create_todo_list": lambda tasks: todo_list.create(tasks) if todo_list else "ToDoList 未初始化",
        "complete_task": lambda result="": todo_list.complete_task(result) if todo_list else "ToDoList 未初始化",
        "save_session_state": save_session_state,
        "get_current_time": get_current_time,
        "search_flight": search_flight,
        "search_train": search_train,
        "search_web": search_web,
        "read_file": read_file,
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
2. create_todo_list - 必用！收到问题后先创建任务清单
3. complete_task - 按清单执行，每完成一步调用一次
4. calculator - 当用户需要计算数学表达式时使用
5. get_weather - 当用户询问天气、需要穿衣建议、想知道某地温度等天气相关问题时使用
6. change_weather_api - 更换天气 API 提供商（当 get_weather 查询失败时使用）
7. get_current_time - 当用户询问当前时间、日期、星期几，或需要根据时间做决策时使用
8. search_flight - 当用户询问机票、航班信息时使用，输入出发地、目的地、日期
9. search_train - 当用户询问火车票、车次信息时使用，输入出发地、目的地
10. search_web - 通用网页搜索，适用于新闻、价格、知识百科、餐厅推荐等各种问题
11. read_file - 当用户要求读取本地文件（PDF、Markdown、txt）时使用，输入完整文件路径

【ToDoList 使用流程 - 强制执行】
1. 收到用户问题后，先在脑中对问题进行思考（不要输出，只是分析）
2. 思考清楚后，调用 create_todo_list 创建任务清单
3. 清单第一步必须是"思考"，分析用户意图和解决方向：
   - 例如：["思考：用户问天气，需要先了解用户在哪/查哪里的天气", "搜索记忆了解上下文", "查询天气", "给出回答"]
4. 创建清单后，按顺序执行每个任务
5. 每完成一个任务，调用 complete_task(result="任务执行结果")
6. 系统会返回下一个任务，继续执行
7. 所有任务完成后，如果清单全部完成，主模型判断是否可以回答用户问题
8. 如果可以回答，给出完整回答；如果还有补充，可以继续

【重要】每次用户发消息，都要重新思考并判断是否需要创建新清单，不是只在第一次创建！

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

def step7_select_session_save_mode(state: dict) -> dict:
    print("\n" + "-" * 40)
    print("📍 选择会话保存方式")
    print(f"   输入 {STEP_BACK} 返回\n")
    print("  1. 自动覆盖（latest.json） - 节约空间，每次只保存一份")
    print("  2. 时间戳保存（latest_xxx.json） - 详细完整，保留历史记录")

    while True:
        c = input(f"\n选择保存方式 (1/2) [{STEP_BACK} 返回]: ").strip()
        if c == STEP_BACK:
            return None
        if c == "1":
            state["session_save_mode"] = "overwrite"
            return state
        if c == "2":
            state["session_save_mode"] = "timestamp"
            return state
        print("无效选择，请输入 1 或 2")

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

    result = step7_select_session_save_mode(state)
    if result is None:
        return get_config()

    base_url = state["base_url"]
    if base_url and not base_url.endswith("/v1"):
        base_url = base_url.rstrip("/") + "/v1"

    save_mode_names = {"overwrite": "自动覆盖（latest.json）", "timestamp": "时间戳（latest_xxx.json）"}

    cfg = {
        "base_url": base_url,
        "api_key": state["api_key"],
        "model": state["model"],
        "provider": state["preset"]["name"],
        "provider_key": state["provider_key"],
        "weather_provider": state["weather_provider"],
        "weather_api_key": state.get("weather_api_key", ""),
        "session_save_mode": state.get("session_save_mode", "overwrite"),
    }

    save_config(cfg)
    config = cfg

    print("\n" + "=" * 50)
    print("✅ 配置完成并已保存!")
    print(f"   AI 提供商: {state['preset']['name']}")
    print(f"   AI 模型: {state['model']}")
    print(f"   天气 API: {state['weather_preset']['name']}")
    print(f"   会话保存: {save_mode_names.get(state.get('session_save_mode', 'overwrite'))}")
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
    global memory, todo_list

    # 初始化记忆系统和任务清单
    memory = Memory()
    todo_list = ToDoList()

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
            # Ctrl+C 退出前自动保存会话状态
            if todo_list and memory:
                save_result = save_session_state(messages)
                print(f"\n{save_result}")
            print("\n\n再见!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            # 退出前自动保存会话状态
            save_result = save_session_state(messages)
            print(f"\n{save_result}")
            print("\n再见!")
            break

        if user_input.lower() == "clear":
            memory.reset()
            todo_list.reset()
            messages = create_messages(weather_provider, "")
            print("✅ 对话已清空，记忆和任务清单已重置")
            continue

        if user_input.lower() == "api choose":
            print("\n📌 正在重新选择配置...")
            return "reconfigure"

        if not user_input:
            continue

        # 如果上一轮任务清单已完成，重置它让模型为新问题重新思考
        if todo_list and todo_list.is_complete():
            todo_list.reset()

        # 检查是否需要生成摘要（每10条消息）
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
