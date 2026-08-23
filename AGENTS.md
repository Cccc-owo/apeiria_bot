# AGENTS.md — Apeiria Bot 开发指南

## 项目定位

Apeiria Bot 是一个 **NoneBot2 项目托管基座**，不是独立框架。NoneBot 负责适配器、事件分发、插件加载、Matcher；
Apeiria 在它之上提供项目化管理、配置体系、插件依赖隔离、Web UI 和 Web 聊天桥接。

当前版本 **不包含 AI Agent**——AI 子系统由独立 initiative 实现。
`webchat` 只是浏览器 ↔ bot 的消息桥接适配器，**不是 AI 子系统**。

## 架构分层（自下而上）

```
L1  config/     — 配置模型 + 四块展开注入 (contract/loader/models/reflector/schema)
    db/         — SQLAlchemy async 引擎 + DbWriteGate + base
L2  db/models/  — ORM 模型 (Session/Message/AccessRule/ApeiriaSetting)
    alembic/    — 数据库迁移
    env/        — .apeiria 插件/适配器环境 (ensure/sync/inject)
L3  bootstrap/  — DAG 启动编排 (拓扑排序 + 步骤)
    cli/        — Click CLI (init/run/reset_password)
    conversation/ — 消息持久化 (框架服务, NoneBot 钩子)
    access/     — RBAC 权限 (event_preprocessor 钩子)
    plugin/     — 插件/适配器管理基础设施 (scanner/manager/adapter_*)
    jobs/       — 长时任务执行 (git 更新 / package 安装)
L4  builtin_plugins/ — 7 个内置 NoneBot 插件
L5  web/        — Web UI API (认证/任务/插件更新/日志)
    webchat/    — 自研 WebChat 适配器 (WS 桥接浏览器)
    webui/      — 前端源码 (Vue3 + Vite + TS + Tailwind + shadcn)
```

## 核心约束

### 必须遵守

1. **NoneBot 是框架，不要封装替代它。** Adapter、Matcher、Driver、`get_plugin_config()` 全部用 NoneBot 原生。
2. **配置统一为 `data/config.yaml` 四块结构：** `nonebot` / `plugins` / `adapters` / `apeiria`。
   前三块启动时通过 `expand_config()` 注入 `os.environ`，`apeiria` 块仅代码读取。
   `.env` 是兜底配置，不作为主源。
3. **插件是标准 NoneBot 插件。** 用 `PluginMetadata` + `get_plugin_config()` 原生机制。
   不引入自定义插件抽象、不要求 `metadata.yaml`、不要求 `Plugin` 基类。
4. **插件/适配器环境隔离。** `.apeiria/` 独立 venv，`site.addsitedir()` 注入。
   框架 `uv.lock` 与插件依赖物理隔离。
5. **消息持久化是框架服务（非插件）。** `apeiria/conversation/` 通过 NoneBot 钩子自动记录。
6. **权限是 event_preprocessor 钩子。** 超级用户绕过，allow/deny 优先级链，阻断在 handler 执行之前。
7. **插件状态在 `.apeiria/plugins.yaml`。** `states` 存 `{"enabled": bool}`，缺省（不在 states 中）视为启用。
   `plugin_states` DB 表不存在——状态不在数据库里。适配器状态同理存于 `.apeiria/adapters.yaml`。
8. **内置插件在 `builtin_plugins/`。** 插件管理基础设施在 `plugin/`。二者分离。
9. **日志用 `from nonebot.log import logger`。** 不引入额外的日志库。
10. **跨平台信息用 `nonebot-plugin-uninfo`。** 不自己封装适配器 API。

### 禁止事项

- **禁止在 domain 层导入 NoneBot 框架对象**（adapter、matcher、driver 等）。
  基础设施层（bootstrap、cli、conversation hooks、access hooks、builtin_plugins、web、webchat、jobs、plugin）可以使用 NoneBot API。
- **禁止引入自定义插件约定。** 插件不需要额外的 metadata.yaml、Plugin 基类、生命周期钩子。
- **禁止使用 `print()`。** 所有输出用 `logger`。
- **禁止硬编码新依赖。** 添加 PyPI 包前确认项目是否已有替代方案。
- **禁止在 commit message 中使用内部计划术语**（L 数字、T 数字等）。

## 项目结构

```
apeiria_bot/
├── pyproject.toml              ← 框架依赖 (无 AI 库)
├── uv.lock
├── bot.py                      ← 入口: apeiria.cli.main:main
├── webui/                      ← 前端源码 (Vue3 + Vite + TS + Tailwind + shadcn)
│
├── apeiria/
│   ├── cli/                    ← CLI (init/run/reset_password)
│   ├── config/                 ← 配置模型 + 加载/展开/契约反射
│   ├── env/                    ← .apeiria 环境管理 (ensure/sync/inject)
│   ├── bootstrap/              ← DAG 启动编排 + 步骤 (含前端 build 触发)
│   ├── db/                     ← 引擎 + base + models + Alembic
│   │   └── models/             ← Session/Message/AccessRule/ApeiriaSetting
│   ├── conversation/           ← 消息持久化 (框架服务)
│   ├── access/                 ← RBAC 权限
│   ├── plugin/                 ← 插件/适配器管理基础设施 (scanner/manager/adapter_*)
│   ├── jobs/                   ← 长时任务执行 (git 更新 / package 安装)
│   ├── builtin_plugins/        ← 内置 NoneBot 插件
│   │   ├── admin/              ← /status /plugins /restart /插件·适配器·权限管理
│   │   ├── help/               ← /help 渲染
│   │   ├── repeater/           ← 群复读
│   │   ├── trigger_reply/      ← 关键词触发
│   │   ├── friendship/         ← 好友/群审批
│   │   ├── relay/              ← 传话转发
│   │   └── self_revoke/        ← 撤回消息
│   ├── web/                    ← Web UI API (认证/任务/更新/logs/插件元信息)
│   ├── webchat/                ← 自研 WebChat 适配器 (WS 桥接浏览器)
│   └── utils/                  ← 通用工具 (superuser/restart/session)
│
├── .apeiria/                   ← 插件/适配器环境
│   ├── pyproject.toml          ← uv 管理依赖
│   ├── plugins.yaml            ← 插件清单 + 状态 (dirs/packages/states)
│   ├── adapters.yaml           ← 适配器清单 + 状态
│   ├── .venv/                  ← uv sync 结果
│   └── plugins/                ← 用户本地插件
│
├── data/                       ← 运行时数据
│   ├── config.yaml             ← 唯一配置主源 (四块)
│   ├── apeiria.db              ← SQLite
│   └── logs/                   ← 运行日志
│
├── alembic/                    ← 数据库迁移
├── alembic.ini                 ← 数据库迁移配置
└── tests/                      ← 测试
```

## 数据库

SQLite + SQLAlchemy async + Alembic。4 张表：

| 表 | 用途 |
|----|------|
| sessions | 会话 (session_id = `{platform}:{type}:{id}`) |
| messages | 消息 (FK → sessions) |
| access_rules | 权限规则 (subject_type/action/priority) |
| apeiria_settings | Web 认证等 key/value 设置 |

`DbWriteGate` 单写锁序列化所有写入，避免 SQLite "database is locked"。

## 配置体系

四块 YAML 结构，启动时展开：

```yaml
nonebot:              # → os.environ (直接注入)
  host: "127.0.0.1"
  port: 8080
  superusers: []

plugins:              # → os.environ (剥包名注入)
  help:
    expand_commands: true

adapters:             # → os.environ (同上)
  nonebot_adapter_onebot_v11:
    websocket_host: "127.0.0.1"

apeiria:              # → 不进环境，仅代码读取
  database:
    path: "data/apeiria.db"
  web:
    host: "127.0.0.1"
    port: 8080
```

插件/适配器配置热更新：`PUT /api/config/{nonebot,plugins,adapters,apeiria}` → 回写 YAML → 更新 `os.environ` + `driver.config` → 下次 `get_plugin_config()` 自动取到新值。
NoneBot 核心字段 (host/port) 不支持热更新，需重启。

## 开发命令

```bash
uv sync                # 安装依赖
uv run apeiria init    # 项目初始化
uv run apeiria run     # 启动 (--reload 热重载)
uv run ruff check .    # 代码检查
uv run ty check --exclude tests  # 类型检查
uv run pytest          # 运行测试 (nonebug)
uv run alembic upgrade head  # 数据库迁移
uv run alembic revision --autogenerate -m "desc"  # 生成迁移
```

## 测试

使用 `nonebug` (NoneBot2 官方测试框架)。conftest.py 配置了 `after_nonebot_init` 覆盖。
测试聚焦功能验证，不做数值微调。`tests/*` 目录下的 `ANN001`、`PLR2004` 规则做了 per-file-ignore。

```bash
uv run pytest -x -q    # 快速运行
uv run pytest -v       # 详细输出
```

## Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
feat: <description>     ← 新功能
fix: <description>      ← 修复
chore: <description>    ← 工程配置/项目设置
```

**禁止在 commit message 中出现 L 数字、T 数字等内部计划代号。**

## 参考项目

[NoneBot 文档](https://nonebot.dev/)

| 项目 | 路径 | 参考用途 |
|------|------|---------|
| **nonebot2** | `.planning/reference/nonebot2/nonebot/` | 框架源码：Config、get_plugin_config、init、plugin 加载 |
| **旧 apeiria** | `.planning/reference/apeiria_bot/apeiria/` | 内置插件、元信息系统、conversation、access 模式 |
| **旧 apeiria config** | `.planning/reference/apeiria_bot/apeiria/apeiria.config.toml` | 原始 TOML 配置格式 |
| **nonebot-adapter-onebot** | `.planning/reference/adapter-onebot/` | OneBot 适配器实现 |
| **zhenxun_bot** | `.planning/reference/zhenxun_bot/` | 风格参考：内置插件组织方式 |
| **AstrBot** | `.planning/reference/AstrBot/` | Web UI 设计参考 |
| **nb-cli** | `.planning/reference/nb-cli/` | CLI 模式参考 |

### 关键源码位置

| 需要了解的 | 文件 |
|-----------|------|
| NoneBot Config 类 | `.planning/reference/nonebot2/nonebot/config.py` |
| get_plugin_config 实现 | `.planning/reference/nonebot2/nonebot/plugin/__init__.py:174` |
| nonebot.init 实现 | `.planning/reference/nonebot2/nonebot/__init__.py:280` |
| onebot v11 adapter | `.planning/reference/adapter-onebot/nonebot/adapters/onebot/v11/` |

## 后续 Initiative

以下能力已确认需求，由独立 initiative 实现：
- AI Agent 整套 (对话、模型适配、工具、知识库、记忆、人设等)
- QQ 工具插件 (跟随 AI initiative)
- 消息主动同步
