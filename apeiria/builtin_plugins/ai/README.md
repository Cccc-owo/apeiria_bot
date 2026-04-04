<div align="center">

# AI 聊天

_✨ Apeiria 的内置 AI 聊天插件 ✨_

</div>

## 📖 介绍

这是 Apeiria 的内置 AI 聊天插件 v0。

适合这些场景：

- 在群聊中通过 `@bot` 或显式唤起词与 AI 对话
- 在私聊中按当前会话开关使用 AI
- 按会话切换人格
- 在不影响长期记忆设计的前提下清空当前短期上下文

当前版本特性：

- 保守、克制、默认短句
- 仅在明确唤起时考虑回复
- 无主动发言
- 无工具调用
- 无长期记忆

## 💿 安装

<details open>
<summary>作为 Apeiria 内置插件使用</summary>

AI 聊天为 Apeiria 内置插件，默认需要由框架内置插件列表显式加载。

插件模块名：

    apeiria.builtin_plugins.ai

</details>

## ⚙️ 配置

### 插件配置

| 配置项 | 必填 | 默认值 | 说明 |
|:---:|:---:|:---:|:---:|
| `enabled` | 否 | `true` | 是否启用插件默认行为 |
| `persona_prompt` | 否 | 默认简洁人格 | 默认风格补充提示词 |
| `explicit_triggers` | 否 | `[]` | 显式唤起词列表；留空时仅响应 @ |
| `max_window_items` | 否 | `5` | 当前会话短期上下文保留条数 |
| `error_reply_text` | 否 | `""` | 显式触发但模型请求失败时的回退文案；留空时使用当前语言默认文案 |

### 模型配置文件

模型配置保存在 AI 插件 `localstore` 数据目录下的 `model.json`。

默认路径：

```text
data/ai/model.json
```

示例：

```json
{
  "enabled": true,
  "provider": "openai_compatible",
  "base_url": "https://api.openai.com",
  "api_key": "your_api_key",
  "model": "gpt-4o-mini",
  "timeout_seconds": 30.0
}
```

说明：

- `base_url` 可填写服务根地址；如果未带 `/v1`，运行时会自动补齐。
- 短期上下文窗口也保存在同一数据目录下的 `state.json`。

## 🎉 使用

### 指令表

| 指令 | 说明 |
|:---:|:---:|
| `/ai on` | 开启当前会话 AI |
| `/ai off` | 关闭当前会话 AI |
| `/ai status` | 查看当前会话 AI 状态 |
| `/persona list` | 查看可用人格 |
| `/persona show` | 查看当前人格 |
| `/persona use <name>` | 切换当前人格 |
| `/reset` | 清空当前会话短期上下文 |

## 注意

- 当前版本只支持显式唤起，不做自然语义唤起。
- `/reset` 仅清空短期上下文，不影响未来记忆设计。
- 人格只影响风格，不覆盖系统级保守规则。
