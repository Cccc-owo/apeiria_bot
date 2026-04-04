# Backend Guidelines

Back to the index: [`../AGENTS.md`](../AGENTS.md)

## Core principles

### Multi-platform compatibility

- Core logic must use abstract `Event` and `Bot` from NoneBot, not adapter-specific event types.
- Keep adapter-specific code isolated in adapter registration and edge handling layers.
- Be careful when modifying shared event handling; avoid assumptions tied to one platform.

### Security

- Validate user input at API boundaries and command handlers.
- Do not log or expose sensitive material such as tokens, passwords, or private identifiers in public-facing logs.
- Enforce authorization before privileged operations.
- Sanitize user-provided content before rendering it in the Web UI.
- Use SQLAlchemy ORM and parameterized queries rather than handwritten string interpolation.

### Performance

- Avoid blocking work in async handlers.
- Cache expensive operations only where it clearly reduces repeated work.
- Watch for N+1 database access patterns and prefer eager loading when needed.

### User-facing behavior

- Error messages should be explicit and actionable.
- Support i18n for user-facing text.
- Prefer graceful degradation when optional capabilities are unavailable.

## Structural rules

Treat the backend as layered code:

- models: schema and persisted data shape
- services: business logic and orchestration
- hooks/routes: event or HTTP entrypoints delegating into services
- config: configuration reading, validation, and mutation
- utils/shared helpers: low-level reusable helpers without unnecessary side effects

Keep business logic out of persistence models and out of thin route handlers.

## API design

- Use FastAPI dependency injection for sessions and service access.
- Group related endpoints under a shared router.
- Use Pydantic models for request and response validation.
- Return specific status codes and concrete error details.

## Database work

- Manage sessions through shared session providers.
- Prefer eager loading over per-row follow-up queries.
- Keep write flows explicit and easy to review.

## Verification for backend changes

Run what is relevant to the surface you changed:

```bash
ruff check .
ruff format .
pyright
pytest
```

If you touched API behavior, also perform at least one end-to-end route sanity check when practical.
