# Apeiria Web UI

Apeiria 的前端管理界面，基于 Vue 3、Vite、TypeScript 和 Vuetify 构建。

## 功能

- 登录、注册与账户管理
- 仪表盘与运行状态展示
- 核心配置编辑
- 插件列表、启停、配置编辑、安装与升级
- 插件商店浏览与安装任务跟踪
- 权限管理
- 实时日志与历史日志
- Web Chat

## 技术栈

- Vue 3
- Vite
- TypeScript
- Vuetify
- Vue Router
- Pinia
- Vue I18n

## 目录

- `src/main.ts`：应用入口
- `src/App.vue`：根组件
- `src/router/`：路由配置
- `src/views/`：页面视图
- `src/components/`：通用组件
- `src/stores/`：状态管理
- `src/api/`：接口封装
- `src/plugins/`：前端插件初始化
- `src/styles/`：全局样式

## 开发

```bash
pnpm install
pnpm dev
```

## 构建

```bash
pnpm build
```

## 校验

```bash
pnpm lint
pnpm type-check
```

## 脚本

- `pnpm dev`
- `pnpm build`
- `pnpm preview`
- `pnpm build-only`
- `pnpm lint`
- `pnpm type-check`
