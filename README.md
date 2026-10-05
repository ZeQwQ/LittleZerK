# 小小泽

> 一个基于 OpenHarness 架构设计的智能 Agent

## 功能

- 🤖 **多 AI 提供商支持** - MiniMax、DeepSeek、OpenAI、硅基流动等
- 🌤️ **实时天气查询** - 支持 OpenWeatherMap、WeatherAPI、和风天气、免费 API
- 🧠 **分层记忆系统** - 自动摘要，持久化存储
- 🔧 **工具调用** - 模型自主决策何时调用工具
- 💾 **配置持久化** - 下次运行自动加载

## 快速开始

```bash
# 克隆项目
git clone <your-repo-url>
cd openharness-agent-loop

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 安装依赖
pip install openai

# 运行
python3 agent.py
```

## 配置

首次运行会引导配置：
1. 选择 AI 提供商或输入 API 端点
2. 输入 API Key
3. 选择模型
4. 选择天气 API（可选）

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
| `calculator` | 计算数学表达式 |
| `get_weather` | 查询天气 |
| `change_weather_api` | 更换天气 API |

## 项目结构

```
.
├── agent.py              # 主程序
├── 小小泽更新日志.md      # 更新日志
├── README.md             # 本文件
├── .env.example          # 环境变量示例
└── .gitignore            # Git 忽略配置
```

## 技术栈

- Python 3
- OpenAI SDK (OpenAI Compatible API)
- Open-Meteo Weather API (免费)

## 未来版本

### Ver0.4 计划
- 📄 **本地文件读取** - PDF、Markdown 解析与问答
- 📋 **ToDo List** - 任务清单管理
- 🔒 **权限安全** - 隐私信息读取询问
- 🤖 **子 Agent** - 小小小泽
- 🌐 **联网功能** - 搜索网络信息

### Ver0.5 计划
- 📧 **邮箱推送** - 每日天气推送至邮箱

## License

MIT
