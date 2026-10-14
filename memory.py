#!/usr/bin/env python3
"""
Memory 模块 - 分层记忆系统
ver0.5
"""

import os
import json
import time
from openai import OpenAI


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

        # 长期记忆
        self.longterm_memory_file = os.path.join(self.memory_dir, "longterm_memory.json")
        self.longterm_memories = []  # 长期记忆列表
        self.load_longterm_memory()

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

    # ─────────────────────────────────────────────────────────────
    # 长期记忆管理
    # ─────────────────────────────────────────────────────────────

    def load_longterm_memory(self):
        """加载长期记忆"""
        try:
            if os.path.exists(self.longterm_memory_file):
                with open(self.longterm_memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.longterm_memories = data.get("memories", [])
        except Exception:
            self.longterm_memories = []

    def save_longterm_memory(self):
        """保存长期记忆"""
        try:
            with open(self.longterm_memory_file, "w", encoding="utf-8") as f:
                json.dump({
                    "memories": self.longterm_memories,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_longterm_memory(self, content: str, category: str = "用户偏好") -> str:
        """添加长期记忆"""
        if not content or not content.strip():
            return "❌ 记忆内容不能为空"

        # 检查是否已存在相似的记忆
        for mem in self.longterm_memories:
            if mem.get("content") == content:
                return f"⚠️ 该记忆已存在：{content[:50]}..."

        memory_entry = {
            "id": f"ltm_{int(time.time())}",
            "content": content.strip(),
            "category": category,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.longterm_memories.append(memory_entry)
        self.save_longterm_memory()
        return f"✅ 已保存到长期记忆：{content[:50]}..."

    def get_longterm_memories(self, category: str = None) -> str:
        """获取长期记忆"""
        if not self.longterm_memories:
            return "📭 长期记忆为空"

        if category:
            filtered = [m for m in self.longterm_memories if m.get("category") == category]
        else:
            filtered = self.longterm_memories

        if not filtered:
            return f"📭 没有找到「{category}」类别的记忆"

        result = ["📚 长期记忆："]
        for mem in filtered:
            cat = mem.get("category", "未分类")
            content = mem.get("content", "")
            created = mem.get("created_at", "")
            result.append(f"\n[{cat}] {content}")
            result.append(f"   📅 {created}")
        return "\n".join(result)

    def remove_longterm_memory(self, memory_id: str = None, content: str = None) -> str:
        """删除长期记忆（按ID或内容）"""
        if not memory_id and not content:
            return "❌ 请提供记忆ID或内容"

        original_count = len(self.longterm_memories)

        if memory_id:
            self.longterm_memories = [m for m in self.longterm_memories if m.get("id") != memory_id]
        elif content:
            self.longterm_memories = [m for m in self.longterm_memories if m.get("content") != content]

        if len(self.longterm_memories) < original_count:
            self.save_longterm_memory()
            return "✅ 已删除该记忆"
        return "❌ 未找到该记忆"

    def clear_longterm_memory(self) -> str:
        """清空所有长期记忆"""
        self.longterm_memories = []
        self.save_longterm_memory()
        return "✅ 长期记忆已清空"

    def reset(self):
        """重置记忆"""
        self.current_summary = []
        self.message_count = 0
