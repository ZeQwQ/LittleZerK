#!/usr/bin/env python3
"""
Agent 循环模块 - 主循环和工具调用处理
ver0.5
"""

import json
from openai import OpenAI

from memory import Memory
from todolist import ToDoList
from config_manager import WEATHER_PRESETS
from tools import get_tools
from tool_impls import get_tool_impls
from prompts import create_messages
from tool_impls import save_session_state


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

def run_loop(client: OpenAI, model: str, provider: str, weather_provider: str, memory: Memory, todo_list: ToDoList):
    """主循环"""

    tools = get_tools(weather_provider)
    tool_impls = get_tool_impls(weather_provider, memory, todo_list)

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
