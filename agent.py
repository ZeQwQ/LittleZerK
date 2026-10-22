#!/usr/bin/env python3
"""
Minimal OpenHarness-Style Agent Loop - ver0.5
- 模块化架构：memory.py, todolist.py, config_manager.py, tools.py, tool_impls.py, prompts.py, api_detection.py, config_flow.py, agent_loop.py
- AI 模型：用户自由选择
- 天气 API：用户自由选择
- 支持真实天气查询
- 分层记忆系统：自动摘要 + 文档检索
- ToDoList 工具：工作前必须先创建任务清单
- 联网搜索：机票、火车票、网页搜索
- 本地文件读取：PDF、Markdown、txt
"""

import sys

from openai import OpenAI

from memory import Memory
from todolist import ToDoList
from config_manager import VERSION
from config_flow import get_config
from agent_loop import run_loop


# ─────────────────────────────────────────────────────────────
# 入口
# ─────────────────────────────────────────────────────────────

def print_version() -> None:
    """打印版本信息（同时验证运行时依赖是否可用）"""
    try:
        import openai
        openai_version = openai.__version__
    except Exception as e:
        print(f"小小泽 {VERSION}")
        print(f"❌ openai SDK 不可用: {e}")
        sys.exit(1)

    print(f"小小泽 {VERSION}")
    print(f"openai SDK {openai_version}")


def main():
    """主入口"""
    if len(sys.argv) > 1 and sys.argv[1] in ("--version", "-v"):
        print_version()
        return

    config = get_config()

    client = OpenAI(
        api_key=config["api_key"],
        base_url=config["base_url"],
    )

    # 初始化记忆系统和任务清单
    memory = Memory()
    todo_list = ToDoList()

    while True:
        result = run_loop(
            client,
            config["model"],
            config["provider"],
            config.get("weather_provider", "free"),
            memory,
            todo_list
        )

        if result == "reconfigure":
            config = get_config(force_reset=True)
            client = OpenAI(
                api_key=config["api_key"],
                base_url=config["base_url"],
            )
            # 重新初始化记忆和任务清单
            memory = Memory()
            todo_list = ToDoList()
            continue

        break


if __name__ == "__main__":
    main()
