# littlezerk

小小泽 AI 助手 - 基于 OpenHarness 架构的智能对话 Agent，兼容任意 OpenAI 格式的 API。

## 安装

```bash
# 从 npm 仓库安装
npm install -g littlezerk

# 或直接从 GitHub 源码安装
npm install -g ZeQwQ/LittleZerK_ver.0.3
```

安装脚本会自动从 GitHub Releases 下载与你系统匹配的预编译二进制。

## 使用

```bash
littlezerk
```

## 首次使用

首次运行会引导你配置：

1. API 输入方式（端点 / Key / 预设提供商）
2. API Key
3. 模型选择
4. 天气 API 提供商
5. 会话保存方式（覆盖 / 时间戳）

配置保存在 `~/.openharness_agent_config.json`。

## 常用命令

| 命令 | 说明 |
|------|------|
| `quit` | 退出（自动保存会话） |
| `clear` | 清空对话与任务清单 |
| `api choose` | 重新选择 API 配置 |
| `Ctrl+C` | 随时退出（自动保存会话） |

## 支持的平台

| 平台 | 架构 |
|------|------|
| macOS | x64 / arm64 |
| Linux | x64 |
| Windows | x64 |

## 卸载

```bash
npm uninstall -g littlezerk
```
