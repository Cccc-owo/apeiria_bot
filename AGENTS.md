# Development Guide

Development guidelines and best practices for the Apeiria Bot project.

## General Principles

Cross-cutting concerns that apply to all development work.

### Multi-Platform Compatibility

- Core logic must use abstract `Event` and `Bot` from nonebot, never import adapter-specific types.
- Keep adapter-specific code isolated in adapter registration and event handling layers.
- Test with multiple adapters when modifying core event handling.

```python
# ✅ Good: Uses abstract types
from nonebot.adapters import Event, Bot

async def handle_message(bot: Bot, event: Event):
    await bot.send(event, "Hello")

# ❌ Bad: Imports adapter-specific types in core
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
```

### Security

- **Input Validation**: Validate all user input at API boundaries and command handlers.
- **Sensitive Data**: Never log or expose sensitive information (tokens, passwords, user IDs in public logs).
- **Authorization**: Use permission checks before executing privileged operations.
- **XSS Prevention**: Sanitize user-provided content before rendering in web UI.
- **SQL Injection**: Always use parameterized queries via SQLAlchemy ORM.

```python
# ✅ Good: Validates input and checks permissions
@router.post("/api/v1/plugins/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    user: User = Depends(get_current_user),
):
    if not user.has_permission("plugin.manage"):
        raise HTTPException(status_code=403, detail="Permission denied")

    if not plugin_id.isidentifier():
        raise HTTPException(status_code=400, detail="Invalid plugin ID")

    await plugin_service.enable(plugin_id)
```

### Performance

- **Async Operations**: Avoid blocking operations in event handlers; use async/await properly.
- **Caching**: Cache expensive computations and database queries when appropriate.
- **Batch Processing**: Use batch operations for bulk data processing.
- **Database**: Use connection pooling and avoid N+1 queries.

```python
# ✅ Good: Batch query with eager loading
users = await session.execute(
    select(User).options(selectinload(User.permissions))
)

# ❌ Bad: N+1 query problem
users = await session.execute(select(User))
for user in users:
    permissions = await session.execute(
        select(Permission).where(Permission.user_id == user.id)
    )
```

### User Experience

- **Error Messages**: Provide clear error messages with actionable guidance.
- **Internationalization**: Support i18n for all user-facing text.
- **Timezone Handling**: Handle timezone conversions consistently using user preferences.
- **Response Time**: Respond to user actions within 3 seconds or provide progress feedback.
- **Graceful Degradation**: Handle missing optional features gracefully.

```python
# ✅ Good: Clear, actionable error message
raise HTTPException(
    status_code=400,
    detail="Plugin 'example' requires Python 3.10+. Current version: 3.9.7"
)

# ❌ Bad: Vague error message
raise HTTPException(status_code=400, detail="Plugin error")
```

## Backend Development

Guidelines for Python + FastAPI backend development.

### Architecture Layers

Follow the layered architecture in `apeiria/core/`:

- **models/**: SQLAlchemy models, database schema only
- **services/**: Business logic, orchestrates models and external APIs
- **hooks/**: Event handlers, connects nonebot events to services
- **configs/**: Configuration management and validation
- **utils/**: Pure utility functions with no side effects

**Models** - Data structure only:

```python
# ✅ Good: Pure data model
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

# ❌ Bad: Business logic in model
class User(Base):
    def send_notification(self, message: str):  # Business logic
        ...
```

**Services** - Business logic:

```python
# ✅ Good: Service handles business logic
class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: str) -> User | None:
        return await self.session.get(User, user_id)

    async def create_user(self, name: str) -> User:
        user = User(id=generate_id(), name=name)
        self.session.add(user)
        await self.session.commit()
        return user
```

**Hooks** - Event handlers:

```python
# ✅ Good: Hook delegates to service
from nonebot import on_command
from nonebot.adapters import Bot, Event

register_cmd = on_command("register")

@register_cmd.handle()
async def handle_register(bot: Bot, event: Event):
    session = get_session()
    service = UserService(session)
    user = await service.create_user(event.get_user_id())
    await bot.send(event, f"Registered as {user.name}")
```

### API Design

**Routing:**

- Use FastAPI dependency injection for database sessions and services.
- Prefix API routes with `/api/v1/` for versioning.
- Group related endpoints under the same router.

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: AsyncSession = Depends(get_session),
):
    service = UserService(session)
    user = await service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

**Request/Response Models:**

Use Pydantic models for validation:

```python
from pydantic import BaseModel, Field

class UserCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")

class UserResponse(BaseModel):
    id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True  # Enable ORM mode
```

**HTTP Status Codes:**

- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST that creates a resource
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

**Error Handling:**

```python
# ✅ Good: Specific error with context
if not user.has_permission("plugin.manage"):
    raise HTTPException(
        status_code=403,
        detail="Permission 'plugin.manage' required to enable plugins"
    )

# ❌ Bad: Generic error
raise HTTPException(status_code=403, detail="Forbidden")
```

### Database Operations

**Session Management:**

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User))
    return result.scalars().all()
```

**Query Optimization:**

Avoid N+1 queries with eager loading:

```python
# ✅ Good: Eager load relationships
from sqlalchemy.orm import selectinload

users = await session.execute(
    select(User).options(selectinload(User.permissions))
)

# ❌ Bad: N+1 query
users = await session.execute(select(User))
for user in users.scalars():
    # This triggers a separate query for each user
    permissions = await session.execute(
        select(Permission).where(Permission.user_id == user.id)
    )
```

### Testing

Write tests for services and API endpoints:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_user(client: AsyncClient, test_user: User):
    response = await client.get(f"/api/v1/users/{test_user.id}")
    assert response.status_code == 200
    assert response.json()["name"] == test_user.name

@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient):
    response = await client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404
```

## Frontend Development

Guidelines for Vue 3 + Vuetify development.

### General

- Follow existing code style and repository patterns before introducing new ones.
- Prefer small, direct changes over broad UI rewrites unless the task explicitly requires redesign.
- Use `pnpm` for all frontend commands.
- Keep code in TypeScript unless there is a clear reason not to.

### UI Principles

- **KISS**: Keep interactions simple and easy to understand on first use.
- **Minimal Text**: Avoid nonessential subtitles, passive hints, and decorative helper text.
- **User-Facing Language**: Do not expose internal implementation terms such as "override" in user-facing copy.
- **Compact Layouts**: Prefer compact, row-based settings layouts when editing configuration.
- **Meaningful Feedback**: Do not show success or restart-related feedback when nothing actually changed.
- **Disabled States**: Save actions should be disabled when there are no pending changes.
- **Validation**: Invalid input must remain actionable and produce explicit validation errors.

### Stack

- **Framework**: Vue 3 (Composition API) + Vite
- **UI Library**: Vuetify 3
- **State Management**: Pinia (when needed)
- **HTTP Client**: Fetch API or Axios
- **Routing**: Vue Router

### Component Structure

```
web/src/
├── components/       # Reusable components
├── views/           # Page-level components
├── composables/     # Composition API logic
├── stores/          # Pinia stores
├── router/          # Route definitions
└── types/           # TypeScript type definitions
```

### Code Style

```typescript
// ✅ Good: Composition API with TypeScript
<script setup lang="ts">
import { ref, computed } from 'vue'

interface User {
  id: string
  name: string
}

const users = ref<User[]>([])
const activeUsers = computed(() => users.value.filter(u => u.active))

async function loadUsers() {
  const response = await fetch('/api/v1/users')
  users.value = await response.json()
}
</script>

// ❌ Bad: Options API without types
<script>
export default {
  data() {
    return {
      users: []
    }
  }
}
</script>
```

### Verification

- Run `pnpm lint` before committing.
- Run `pnpm type-check` to verify TypeScript types.
- Run `pnpm build` after meaningful changes to ensure production build succeeds.
- Test in browser when modifying user interactions.
- Call out any gaps if browser-side end-to-end verification was not performed.

## Code Quality

Standards for naming, documentation, and code checking.

### Naming Conventions

**Python:**

- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_CASE`
- **Private members**: Prefix with `_`
- **Type variables**: `T`, `KT`, `VT` (single uppercase letter or short PascalCase)

```python
# ✅ Good
class UserService:
    MAX_RETRIES = 3

    def __init__(self):
        self._cache = {}

    async def get_user_by_id(self, user_id: str) -> User | None:
        ...
```

**TypeScript:**

- **Functions/Variables**: `camelCase`
- **Classes/Components**: `PascalCase`
- **Constants**: `UPPER_CASE` or `camelCase`
- **Interfaces/Types**: `PascalCase`
- **Private members**: Prefix with `#` or `_`

```typescript
// ✅ Good
interface UserProfile {
  userId: string
  displayName: string
}

class UserService {
  private readonly cache = new Map()

  async getUserById(userId: string): Promise<User | null> {
    ...
  }
}
```

**Descriptive Names:**

Use descriptive names that reveal intent:

```python
# ✅ Good: Clear intent
async def get_active_users_by_role(role: str) -> list[User]:
    ...

# ❌ Bad: Vague
async def get_users(r: str) -> list:
    ...
```

### Documentation

**Python Docstrings:**

Use Google-style docstrings for all public functions and classes:

```python
async def get_user_by_id(user_id: str) -> User | None:
    """Retrieve a user by their unique identifier.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        The user object if found, None otherwise.

    Raises:
        DatabaseError: If the database query fails.
    """
    ...
```

**Type Hints:**

Always use type hints for function signatures:

```python
# ✅ Good: Full type hints
async def process_users(
    users: list[User],
    filter_fn: Callable[[User], bool] | None = None,
) -> dict[str, User]:
    ...

# ❌ Bad: No type hints
async def process_users(users, filter_fn=None):
    ...
```

**TypeScript JSDoc:**

Add JSDoc for complex functions:

```typescript
/**
 * Fetches user data with retry logic.
 *
 * @param userId - The unique identifier of the user
 * @param maxRetries - Maximum number of retry attempts (default: 3)
 * @returns Promise resolving to user data or null if not found
 * @throws {NetworkError} If all retry attempts fail
 */
async function fetchUser(
  userId: string,
  maxRetries: number = 3
): Promise<User | null> {
  ...
}
```

**Inline Comments:**

Keep inline comments minimal; prefer self-documenting code:

```python
# ✅ Good: Self-documenting
if user.has_permission("admin"):
    await grant_access()

# ❌ Bad: Unnecessary comment
# Check if user is admin
if user.role == "admin":
    await grant_access()

# ✅ Good: Explains non-obvious logic
# Use exponential backoff to avoid overwhelming the API
await asyncio.sleep(2 ** retry_count)
```

### Code Checking

**Python:**

Run these tools before committing:

```bash
# Linting and formatting
ruff check .
ruff format .

# Type checking
pyright

# Run tests
pytest
```

**TypeScript:**

Run these tools before committing:

```bash
cd web
pnpm lint        # ESLint
pnpm type-check  # TypeScript compiler
pnpm build       # Production build
```

### Error Handling

**Catch Specific Exceptions:**

```python
# ✅ Good: Catch specific exceptions
try:
    user = await get_user_by_id(user_id)
except DatabaseError as e:
    logger.error(f"Database error fetching user {user_id}: {e}")
    raise HTTPException(status_code=500, detail="Database error")
except ValidationError as e:
    logger.warning(f"Invalid user ID {user_id}: {e}")
    raise HTTPException(status_code=400, detail="Invalid user ID")

# ❌ Bad: Bare except
try:
    user = await get_user_by_id(user_id)
except:
    raise HTTPException(status_code=500, detail="Error")
```

**Structured Logging:**

Use `loguru` with context:

```python
from loguru import logger

# ✅ Good: Includes context
logger.info(
    "User login successful",
    user_id=user.id,
    ip_address=request.client.host,
)

# ❌ Bad: No context
logger.info("Login successful")
```

**Log Levels:**

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for recoverable issues
- `ERROR`: Error messages for failures
- `CRITICAL`: Critical errors that may cause system failure

```python
logger.debug(f"Cache hit for key {key}")
logger.info(f"User {user_id} registered successfully")
logger.warning(f"Rate limit approaching for user {user_id}")
logger.error(f"Failed to send notification to user {user_id}: {error}")
logger.critical(f"Database connection lost: {error}")
```

## Git Workflow

Branching strategy, commit conventions, and PR process.

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

**Format:**

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `chore`: Build process or auxiliary tool changes
- `ci`: CI/CD configuration changes
- `revert`: Revert a previous commit

**Scope (Optional):**

- `core`: Core framework
- `webui`: Web UI
- `api`: API layer
- `cli`: CLI commands
- `plugin`: Plugin system
- `config`: Configuration management
- `db`: Database layer

**Subject:**

- Use imperative mood: "add" not "added" or "adds"
- Don't capitalize first letter
- No period at the end
- Limit to 50 characters

**Body (Optional):**

- Explain what and why, not how
- Wrap at 72 characters
- Separate from subject with a blank line

**Footer (Optional):**

- Reference issues: `Closes #123`, `Fixes #456`
- Breaking changes: `BREAKING CHANGE: description`

**Examples:**

```
feat(webui): add user profile page

Add a new user profile page with avatar upload and bio editing.
Users can now customize their profile information.

Closes #234
```

```
fix(core): resolve plugin loading race condition

Plugin dependencies were not being loaded in the correct order,
causing intermittent failures on startup. This fix ensures
plugins are loaded in topological order based on dependencies.

Fixes #567
```

```
docs(readme): update Docker deployment guide

- Add docker-compose.yml example
- Document volume mount requirements
- Clarify environment variable usage
```

### Branching Strategy

**Main Branches:**

- `main`: Production-ready code
- `develop`: Integration branch for features (if using Git Flow)

**Feature Branches:**

Create feature branches from `main` (or `develop`):

```bash
git checkout -b feat/user-profile
git checkout -b fix/plugin-loading
git checkout -b docs/api-guide
```

**Branch Naming:**

- `feat/<feature-name>`: New features
- `fix/<bug-name>`: Bug fixes
- `docs/<doc-name>`: Documentation
- `refactor/<refactor-name>`: Refactoring
- `test/<test-name>`: Tests

Use kebab-case for branch names.

### Pull Request Process

**Before Creating PR:**

1. Update from main:
   ```bash
   git checkout main
   git pull origin main
   git checkout feat/your-feature
   git rebase main
   ```

2. Run checks:
   ```bash
   # Python
   ruff check .
   ruff format .
   pyright
   pytest

   # Frontend
   cd web
   pnpm lint
   pnpm type-check
   pnpm build
   ```

3. Commit with conventional format:
   ```bash
   git add .
   git commit -m "feat(webui): add user profile page"
   ```

**PR Title:**

Use the same format as commit messages:

```
feat(webui): add user profile page
fix(core): resolve plugin loading race condition
```

**Review Process:**

- At least one approval required before merging
- Address all review comments
- Keep PR focused and reasonably sized (< 500 lines if possible)
- Squash commits if there are many small fixup commits

**Merging:**

- Use "Squash and merge" for feature branches
- Use "Rebase and merge" for small fixes
- Delete branch after merging
