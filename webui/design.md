---
version: alpha
name: Apeiria WebUI
description: Apeiria Bot 管理面板的视觉系统 —— 参照 Material You(Material 3)的系统控制台气质:tonal 表面、离散海拔、状态层、大圆角、权重式排印;由 shadcn-vue + Tailwind v4 实现,蓝为唯一主色、紫为 tertiary 点缀。
colors:
  primary: "#1565C0"
  on-primary: "#FFFFFF"
  primary-container: "#D8E3FF"
  on-primary-container: "#06325A"
  secondary: "#5B6472"
  on-secondary: "#FFFFFF"
  secondary-container: "#DBE2EE"
  on-secondary-container: "#2A3546"
  tertiary: "#7C3AED"
  on-tertiary: "#FFFFFF"
  tertiary-container: "#EADDFF"
  on-tertiary-container: "#38156B"
  success: "#0E8A5F"
  warning: "#B26A00"
  error: "#DC2626"
  on-error: "#FFFFFF"
  error-container: "#F7D6D6"
  on-error-container: "#6E1B1B"
  background: "#F6F7F9"
  surface: "#FFFFFF"
  on-surface: "#1B1C1F"
  on-surface-variant: "#45474E"
  surface-container-low: "#F0F1F4"
  surface-container: "#E9EBEF"
  surface-container-high: "#E3E5E9"
  surface-dim: "#D8DBE0"
  outline: "#73777F"
  outline-variant: "#C5C8D0"
  inverse-surface: "#303237"
  inverse-on-surface: "#F1F2F5"
  scrim: "#000000"
  shadow: "#000000"
states:
  on-surface-hover: "rgba(27, 28, 31, 0.08)"
  on-surface-focus: "rgba(27, 28, 31, 0.12)"
  on-surface-pressed: "rgba(27, 28, 31, 0.12)"
  on-surface-selected: "rgba(27, 28, 31, 0.08)"
  on-surface-drag: "rgba(27, 28, 31, 0.16)"
  on-primary-hover: "rgba(255, 255, 255, 0.08)"
  on-primary-pressed: "rgba(255, 255, 255, 0.12)"
  on-tertiary-hover: "rgba(255, 255, 255, 0.08)"
typography:
  display:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 2rem
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.02em
  headline:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 1.25rem
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: -0.01em
  title-medium:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 1rem
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0.005em
  body-large:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 1rem
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: 0.03em
  body-medium:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 0.875rem
    fontWeight: 400
    lineHeight: 1.43
    letterSpacing: 0.02em
  label-medium:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 0.75rem
    fontWeight: 500
    lineHeight: 1.33
    letterSpacing: 0.04em
  metric:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: 2rem
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -0.02em
rounded:
  xs: 8px
  sm: 10px
  md: 12px
  lg: 16px
  xl: 28px
  pill: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 40px
  grid: 8px
elevation:
  0: "none"
  1: "0 1px 2px 0 rgba(0, 0, 0, 0.06)"
  2: "0 1px 3px 0 rgba(0, 0, 0, 0.07), 0 10px 24px -8px rgba(0, 0, 0, 0.07)"
components:
  app-background:
    backgroundColor: "{colors.background}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 24px
    elevation: "{elevation.1}"
    surfaceTint: "{colors.primary}"
  stat-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    rounded: "{rounded.lg}"
    padding: 24px
    typography: "{typography.metric}"
  text-muted:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.label-medium}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.md}"
    height: 36px
    elevation: "{elevation.1}"
    typography: "{typography.body-medium}"
  button-primary-hover:
    stateLayer: "{states.on-primary-hover}"
  button-secondary:
    backgroundColor: "{colors.secondary-container}"
    textColor: "{colors.on-secondary-container}"
    rounded: "{rounded.md}"
    height: 36px
  button-tertiary:
    backgroundColor: "{colors.tertiary}"
    textColor: "{colors.on-tertiary}"
    rounded: "{rounded.md}"
    height: 36px
  button-text:
    color: "{colors.primary}"
    rounded: "{rounded.md}"
    height: 36px
  button-outlined:
    border: "1px solid {colors.outline}"
    color: "{colors.primary}"
    rounded: "{rounded.md}"
    height: 36px
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    border: "1px solid {colors.outline}"
    rounded: "{rounded.md}"
    height: 40px
    labelColor: "{colors.on-surface-variant}"
  sidebar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
  sidebar-item-active:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    rounded: "{rounded.md}"
  topbar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    height: 64px
  icon-chip-primary:
    backgroundColor: "{colors.primary-container}"
    color: "{colors.on-primary-container}"
  badge-info:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    rounded: "{rounded.sm}"
  badge-success:
    backgroundColor: "{colors.tertiary-container}"
    textColor: "{colors.on-tertiary-container}"
    rounded: "{rounded.sm}"
  badge-warning:
    backgroundColor: "color-mix(in srgb, {colors.tertiary-container} 60%, {colors.surface})"
    textColor: "{colors.on-tertiary-container}"
    rounded: "{rounded.sm}"
  badge-destructive:
    backgroundColor: "{colors.error-container}"
    textColor: "{colors.on-error-container}"
    rounded: "{rounded.sm}"
  status-online:
    backgroundColor: "{colors.success}"
  status-offline:
    backgroundColor: "{colors.error}"
  divider:
    backgroundColor: "{colors.outline-variant}"
  focus-ring:
    backgroundColor: "{colors.primary}"
  state-hover:
    backgroundColor: "color-mix(in srgb, {colors.primary} 8%, transparent)"
  state-pressed:
    backgroundColor: "color-mix(in srgb, {colors.primary} 12%, transparent)"
---

## Overview

Apeiria WebUI 是 Apeiria Bot 的管理面板,面向机器人主人/运维者。视觉参照 Material You 的**系统控制台**:不再是 Berry 那种"浮起柔影 + 发丝描边"的 SaaS 卡片,而是 Material 3 那种**平坦而有秩序的 tonal 表面**——卡片是一层"表面",用**状态层 + 离散海拔 + surface tint** 表达层级,而不是靠硬边框。

气质是"安静、精确、可信赖"。信息密度适中,动效克制,让插件/适配器/配置/日志这些数据驱动的内容成为主角。技术上完全由 shadcn-vue + Tailwind v4 复刻 Material 3 的**设计角色与机制**,不引入 Vuetify/daisyUI,也不引入 Roboto——中文场景用系统字体栈。

> 一句话锚点:**它看起来像一个懂 Material You 的系统控制台**——冷静的蓝、克制的紫、柔和的圆角、安静的状态层。

## Colors

调色板遵循 Material 3 的角色模型:每个角色都有一对「底色 + on 色」,以及一个 tonal 的 container。**蓝是唯一主色**,紫是 tertiary(re只做强调/图表/次级),避免多彩竞争。

- **primary (#1565C0) / on-primary (#FFF)**:唯一交互色。主按钮底、链接文字、焦点环、激活项文字。`#1565C0` 对白字达 AA。
- **primary-container (#D8E3FF) / on-primary-container (#06325A)**:主色浅 tint。用于图标片、信息徽章、激活侧边项、选中态背景——**用 tonal 容器替代实色底**,这是 M3 的关键。
- **tertiary (#7C3AED) / tertiary-container (#EADDFF) / on-tertiary-container (#38156B)**:紫色只做点缀与强调:图表、次级强调按钮、成功徽章。**它绝不与 primary 争夺主交互。**
- **secondary (#5B6472) / secondary-container (#DBE2EE) / on-secondary-container (#2A3546)**:中性蓝灰,用于次级按钮底、次级区域底。
- **background (#F6F7F9) / surface (#FFF) / on-surface (#1B1C1F)**:页底(浅冷灰)与卡片(纯白)。**on-surface 用近黑而非纯黑**,更柔和。
- **on-surface-variant (#45474E)**:次要文字、说明文字,替代单一的灰。
- **outline (#73777F) / outline-variant (#C5C8D0)**:输入/边框用 `outline`,分隔线/弱描边用 `outline-variant`。
- **surface-container-low/…/high**:辅助表面的三档阶梯(弹窗、悬浮、tooltip 递进)。
- **语义色**:error 及其 error-container;success/warning 用 tertiary-container 与混合色承托(达对比)而非饱和实色。
- **状态层**:见 [Elevation & Depth](#elevation--depth),用 `states.*` 的 alpha 值表达 hover/focus/pressed,不换底色。

## Typography

中文为主,采用**系统字体栈**(含 PingFang SC / Microsoft YaHei 回退),不引入 Roboto/Noto;M3 的**权重与字距**才是被采纳的东西。

- **display** 32px / 600 / −0.02em:仪表盘大数字、页面主标题。
- **headline** 20px / 600 / −0.01em:区块标题。
- **title-medium** 16px / 600 / +0.005em:卡片标题。
- **body-large / body-medium** 16 / 14px / 400 / 正字距:正文与表格。
- **label-medium** 12px / 500 / +0.04em:辅助文字、徽章、元信息。
- **metric** 32px / 700 / −0.02em:统计卡大数字。

> 不做大写按钮(CJK 大写无意义),层级靠**字重 + 字距 + 字号**,而非 letter-spacing 拉满的全大写。

## Layout

沿用「左侧边栏 + 顶栏 + 内容区」骨架,间距以 **8dp 网格** 为节拍(`spacing.grid = 8`,小件用 4)。内容区浅灰底 + 容器栅格,卡片内距 24、页面边距 24–32。

- **侧边栏**:默认 260px,可折叠 72px 图标轨(状态持久化);当前项用 `sidebar-item-active`(primary-container 圆形胶囊)。
- **顶栏**:64px,悬浮于内容之上,含标题/面包屑、主题切换、账号菜单。
- **内容区**:`app-background` + 栅格;列表页统一「标题 + 操作 + 搜索」页头。

## Elevation & Depth

Material 3 用**海拔 + surface tint** 表达深度,而非阴影叠加或硬边框。

- **卡片(elevation 1)**:纯白表面 + 柔和一级阴影 + 一层**极淡的 primary surface tint**(`color-mix(in srgb, primary 4%, transparent)` 叠加)营造 M3 的"浮动亮表面"。
- **弹窗/菜单(elevation 2+)**:更高的 `surface-container-high` 底色 + 二级阴影,层级更高但始终保持平坦。
- **状态层(State layer)**:hover / focus / pressed 用 `on-surface` 或颜色自身的 **alpha 叠加**,例如 `on-surface 8%`(hover)、`12%`(focus/pressed)、`16%`(drag)。主按钮 hover 用 `on-primary`(白)8% 叠加提亮。**这是本系统的核心交互机制——所有可交互元素都必须有状态层反馈。**
- **禁止**厚重的实色投影与发丝描边承载层级(描边只用于 outline 按钮/输入框)。

## Shapes

统一 M3 形状族:`xs 8 / sm 10 / md 12 / lg 16 / xl 28`。卡片用 `lg`(16),按钮/输入用 `md`(12),徽章等小件用 `sm`(10),对话框等大容器用 `xl`(28)。圆角随层级拉开,内紧外松。

## Components

- **button-primary**:纯 primary 实底 + on-primary 白字,hover/pressed 用**白色状态层**叠加(提亮,不换色)。
- **button-secondary / tertiary**:tonal 容器底(secondary-container / tertiary-container)+ 对应 on 色;tertiary 用于强调性但非主操作。
- **button-text / outlined**:文字/描边按钮,颜色用 `colors.primary`。outlined 用 1px `outline` 描边。
- **card / stat-card**:纯白 + 一级海拔 + 极淡 surface tint。统计卡为纯白 + 彩色 tonal 图标片 + metric 大数字,无渐变。
- **input**:白底、`rounded.md`、1px `outline` 描边、focus 转 primary ring。
- **sidebar / sidebar-item-active / topbar**:见 Layout;激活项用 primary-container 胶囊。
- **icon-chip-primary**:primary-container 浅蓝图标片,承托统计卡/列表项图标。
- **badge-info/-success/-warning/-destructive**:tonal/tint 底 + 同系深字(均达 AA)。warning 用 tertiary-container 与白混合以软化。
- **status-online / -offline**:纯色状态点(绿/红)。
- **divider**:1px,填充 `outline-variant`,用于内容内部分隔。
- **focus-ring**:primary 焦点环,保证键盘可达。

## Do's and Don'ts

- **Do** 用 tonal 容器(primary-container/tertiary-container)承载选中、徽章、图标,而非饱和色直接铺底配白字。
- **Do** 用**状态层**(alpha 叠加)表达 hover/focus/pressed。**Don't** 用 `hover:bg-primary/90` 这种"换色"的方式。
- **Do** 蓝承担唯一主交互,紫(tertiary)只做强调/图表。**Don't** 让多色争夺注意力。
- **Do** 用离散海拔 + surface tint + outline-variant 表达层级。**Don't** 用厚实阴影或发丝描边堆叠。
- **Do** 圆角随层级拉开(卡片 16 / 控件 12 / 徽章 10 / 大容器 28)。**Don't** 全局统一小圆角或全大圆角。
- **Do** 权重 + 字距 + 字号表达排印层级。**Don't** 拉满全大写做按钮。
- **Do** 动效克制(折叠过渡、状态层淡入、骨架屏、toast 滑入),用 transform/opacity。**Don't** 堆砌花哨动画。
- **Do** 语义/错误色用浅 tint 底 + 深字与状态点,保证可读。**Don't** 用饱和色铺底配白字。
