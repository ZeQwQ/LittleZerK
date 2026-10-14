#!/usr/bin/env python3
"""
工具定义模块 - 工具的 JSON Schema 定义
ver0.5
"""


def get_tools(weather_provider: str = None):
    """获取工具定义列表（用于 API 调用）"""
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
        },
        {
            "type": "function",
            "function": {
                "name": "add_longterm_memory",
                "description": "添加信息到长期记忆。用于保存用户偏好、重要信息等永久性内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "要保存的记忆内容"},
                        "category": {"type": "string", "description": "记忆分类，如'用户偏好'、'重要信息'、'习惯要求'等"}
                    },
                    "required": ["content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_longterm_memories",
                "description": "获取长期记忆中的所有内容。回答用户问题前可以先调用此工具获取用户偏好和重要信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "按分类筛选记忆，如'用户偏好'，不填则返回全部"}
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "remove_longterm_memory",
                "description": "删除长期记忆中的指定内容。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string", "description": "记忆ID"},
                        "content": {"type": "string", "description": "记忆内容（二选一）"}
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
