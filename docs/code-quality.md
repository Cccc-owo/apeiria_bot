# Code Quality

Back to the index: [`../AGENTS.md`](../AGENTS.md)

## Naming

### Python

- functions and variables: `snake_case`
- classes: `PascalCase`
- constants: `UPPER_CASE`
- internal/private members: leading `_`

### TypeScript

- functions and variables: `camelCase`
- classes and components: `PascalCase`
- interfaces and types: `PascalCase`
- constants: `UPPER_CASE` or established local convention

Use descriptive names that reveal intent.

## Documentation style

- Prefer self-explanatory code over excessive inline commentary.
- Add comments only where the reasoning is not obvious from the code itself.
- Keep user-facing documentation in the canonical doc for that topic.
- Keep `AGENTS.md` short and use it to route readers to detailed docs.

## Error handling and logging

- Catch specific exceptions instead of using bare `except`.
- Include actionable context in errors and logs.
- Use structured logging where available.

## Verification checklist

### Python work

```bash
ruff check .
ruff format .
pyright
pytest
```

### Frontend work

```bash
cd web
pnpm lint
pnpm type-check
pnpm build
```

## Git and review expectations

- Prefer focused changes over broad unrelated cleanup.
- Follow Conventional Commit style when writing commits.
- Before opening or finalizing a change, verify that the relevant checks for the touched area have run.
- Keep documentation changes consistent across hub docs and canonical leaf docs.
- If you move guidance between docs, update inbound links in `AGENTS.md`, `README.md`, and any affected leaf `README.md` files in the same change.
