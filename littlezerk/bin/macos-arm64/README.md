# 小小泽

> 一个基于 OpenHarness 架构设计的智能 Agent（ver0.5）

## 功能

- 🤖 **多 AI 提供商支持** - MiniMax、DeepSeek、OpenAI、硅基流动等，想用哪个用哪个 😎
- 🌤️ **实时天气查询** - 支持 OpenWeatherMap、WeatherAPI、和风天气、免费 API，随时知道天气变化 ☀️
- 🧠 **分层记忆系统** - 自动摘要 + 持久化存储，再长的对话也能记住重点 🧠
- 🔧 **工具调用** - 模型自主决策什么时候该用什么工具，聪明又靠谱 🛠️
- 💾 **配置持久化** - 下次运行自动加载，不用重复配置，省心省力 💾
- 🔒 **安全计算器** - 使用 AST 解析，防止代码注入，算数学题既快又安全 🔢
- 📋 **ToDoList 清单** - 工作前必须创建清单，有条不紊步步为营 ✅
- 🌐 **联网搜索** - 机票、火车票、网页信息，想搜什么搜什么 🔍
- 📄 **本地文件读取** - 读取 PDF、Markdown、txt，基于文档内容回答问题 📖

## 快速开始

### 方式一：npm 安装（推荐）

```bash
npm install -g littlezerk
littlezerk
```

### 方式二：从源码运行

```bash
# 克隆项目
git clone https://github.com/ZeQwQ/LittleZerK_ver.0.3.git
cd LittleZerK_ver.0.3

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
python3 agent.py
```

## 配置

首次运行会引导配置：
1. 选择 AI 提供商或输入 API 端点
2. 输入 API Key
3. 选择模型
4. 选择天气 API（可选）
5. 选择会话保存方式（覆盖/时间戳）

配置保存在 `~/.openharness_agent_config.json`

## 命令

| 命令 | 说明 |
|------|------|
| `quit` | 退出 |
| `Ctrl+C` | 随时退出 |
| `clear` | 清空对话 |
| `api choose` | 重新选择配置 |

## 工具

| 工具 | 功能 |
|------|------|
| `calculator` | 计算数学表达式（AST 安全解析） |
| `search_memory` | 搜索对话历史上下文 |
| `create_todo_list` | 创建任务清单 |
| `complete_task` | 标记任务完成，获取下一个 |
| `get_weather` | 查询天气 |
| `change_weather_api` | 更换天气 API |
| `save_session_state` | 保存会话状态（覆盖/时间戳模式） |
| `get_current_time` | 获取当前日期和时间 |
| `search_flight` | 搜索机票信息 |
| `search_train` | 搜索火车票信息 |
| `search_web` | 通用网页搜索 |
| `read_file` | 读取本地文件（PDF、Markdown、txt） |
| `add_longterm_memory` | 添加信息到长期记忆 |
| `get_longterm_memories` | 获取长期记忆内容 |
| `remove_longterm_memory` | 删除指定长期记忆 |

## ver0.4 → ver0.5 更新速览

| 类别 | 更新内容 |
|------|----------|
| 🏗️ 模块化重构 | agent.py 从 1737 行拆分为 9 个模块，主入口仅 64 行 📦 |
| 🧩 高内聚低耦合 | 模块间通过参数传递依赖，便于独立测试和维护 🔧 |
| 📦 打包兼容 | Nuitka 自动追踪导入，npm 包无需修改 🚀 |
| 🧠 长期记忆 | 新增永久记忆系统，保存用户偏好和重要信息 💾 |

---

## 项目结构

```
.
├── agent.py              # 主入口
├── memory.py             # 记忆系统模块
├── todolist.py           # 任务清单模块
├── config_manager.py      # 配置管理模块
├── tools.py              # 工具定义模块
├── tool_impls.py         # 工具实现模块
├── prompts.py            # 提示词模板模块
├── api_detection.py       # API 自动检测模块
├── config_flow.py        # 配置流程模块
├── agent_loop.py         # Agent 主循环模块
├── 小小泽更新日志.md      # 更新日志
├── 面试可能的问题.md      # 面试问题整理
├── README.md             # 本文件
├── conversations/        # 对话记录保存
├── littlezerk/           # npm 包源码
│   ├── package.json      # npm 包配置
│   ├── index.js          # npm 入口
│   ├── bin/run.js        # CLI 入口
│   └── scripts/          # 脚本
├── .github/workflows/    # GitHub Actions
├── .env.example          # 环境变量示例
└── .gitignore            # Git 忽略配置
```

## 技术栈

- Python 3
- OpenAI SDK (OpenAI Compatible API)
- Open-Meteo Weather API (免费)

## 未来版本

### Ver0.6 计划
- 🔒 **权限安全** - 提升小小泽安全意识，做好权限拦截，不读取用户隐私信息（或读取前询问）🤐
- 🤖 **子 Agent** - 添加小小小泽（子 Agent），让小小泽可以做更多事 🧐
- 📧 **邮箱推送** - 每日天气推送至邮箱，温暖人心 🤗

## License

MIT
