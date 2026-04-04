# Frontend Guidelines

Back to the index: [`../AGENTS.md`](../AGENTS.md)

## General rules

- Follow existing repository patterns before introducing new ones.
- Prefer small, direct UI changes over broad rewrites unless the task explicitly requires redesign.
- Use `pnpm` for frontend commands.
- Keep frontend code in TypeScript unless there is a clear reason not to.

## UI principles

- Keep interactions simple and understandable on first use.
- Avoid nonessential helper text and decorative copy.
- Do not expose internal implementation terms in user-facing language.
- Prefer compact, row-based layouts for settings and configuration editors.
- Do not show success or restart messaging when nothing actually changed.
- Disable save actions when there are no pending changes.
- Invalid input must stay actionable and show explicit validation feedback.

## Stack expectations

- Vue 3 with Composition API
- Vuetify for UI components
- Pinia when shared client state is needed
- Vue Router for navigation
- Fetch or Axios for HTTP access

## Source layout

- `web/src/components/` — reusable components
- `web/src/views/` — page-level views
- `web/src/composables/` — reusable Composition API logic
- `web/src/stores/` — Pinia stores
- `web/src/router/` — routing
- `web/src/api/` — HTTP client wrappers and API modules
- `web/src/types/` — TypeScript types

See local leaf docs where available:

- [`../web/src/components/README.md`](../web/src/components/README.md)
- [`../web/src/plugins/README.md`](../web/src/plugins/README.md)
- [`../web/src/styles/README.md`](../web/src/styles/README.md)

## Verification for frontend changes

Run what is relevant before finishing:

```bash
cd web
pnpm lint
pnpm type-check
pnpm build
```

Also verify browser behavior when you changed interaction flows, validation, navigation, or rendering.
