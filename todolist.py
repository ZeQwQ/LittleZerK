#!/usr/bin/env python3
"""
ToDoList 模块 - 任务清单系统
ver0.5
"""


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
