# apeiria_bot

## Environment Setup

This project uses `uv` to manage two environments:

1. the main project environment in `.venv`
2. the user extension environment in `.apeiria/extensions/.venv`

Before initialization, make sure the machine has:

1. Python 3.10+
2. `uv`

Some plugins may still require extra system libraries depending on the platform.

### Local Development

For local development, install frontend tooling if Web UI assets may need to build
or rebuild on startup:

1. `node`
2. `pnpm` or `npm`

User-managed project files:

1. `apeiria.config.toml`
2. `apeiria.plugins.toml`
3. `apeiria.adapters.toml`
4. `apeiria.drivers.toml`
5. `.env`
6. `.env.dev`
7. `.env.prod`

Create `apeiria.*.toml` from the example files before first run:

1. `cp apeiria.config.example.toml apeiria.config.toml`
2. `cp apeiria.plugins.example.toml apeiria.plugins.toml`
3. `cp apeiria.adapters.example.toml apeiria.adapters.toml`
4. `cp apeiria.drivers.example.toml apeiria.drivers.toml`

`apeiria init` only creates missing `.env`, `.env.dev`, and `.env.prod` as empty
files. It does not create or rewrite any `apeiria.*.toml`.

Generated state:

1. `.apeiria/extensions/`
2. `.apeiria/cache/`
3. `data/`

## How to start

1. clone the repository
2. install project environment using `uv sync --locked`
3. activate the virtual environment
4. POSIX shells: `source .venv/bin/activate`
5. create `apeiria.*.toml` from the example files
6. initialize the project and user extension environments using `apeiria init`
7. install user plugins using `apeiria plugin install <package>`
8. run your bot using `apeiria run`
9. if you need to rebuild Web UI assets before startup, use `apeiria run --build`

## Environment Management

After activating `.venv`, use these commands:

1. `apeiria init`
   create missing empty `.env*` files, then sync the main project environment and the user extension environment
2. `apeiria init --no-dev`
   sync the main project environment without development dependencies
3. `apeiria repair`
   re-sync both environments from current managed files
4. `apeiria env info`
   show current environment paths and status
5. `apeiria run --build`
   build Web UI frontend assets, then run the bot

Main environment responsibilities:

1. runtime for the Apeiria project itself
2. framework and built-in project dependencies

User extension environment responsibilities:

1. user-installed plugins
2. user-installed adapters
3. user-installed drivers

The extension environment is managed under `.apeiria/extensions/` and is ignored by git.
If `APEIRIA_CONFIG_DIR` is set, Apeiria reads and writes `apeiria.*.toml` in that
directory instead of the project root.
`apeiria init` does not create or rewrite these TOML files.

## User Packages

Use Apeiria commands to manage packages in the user extension environment:

1. `apeiria plugin install <package>`
2. `apeiria adapter install <package>`
3. `apeiria driver install <package>`

Installed user packages are declared in `.apeiria/extensions/pyproject.toml`.
Their project registrations remain in these files:

1. `apeiria.plugins.toml`
2. `apeiria.adapters.toml`
3. `apeiria.drivers.toml`

When `APEIRIA_CONFIG_DIR` is set, these files are created in that directory.
Example config files are kept in the project root:

1. `apeiria.config.example.toml`
2. `apeiria.plugins.example.toml`
3. `apeiria.adapters.example.toml`
4. `apeiria.drivers.example.toml`

To move local runtime state to another machine:

1. export local state with `apeiria env export`
2. clone the repo on the new machine
3. install project environment using `uv sync --locked`
4. activate the virtual environment
5. POSIX shells: `source .venv/bin/activate`
6. initialize environments with `apeiria init`
7. import local state with `apeiria env import .apeiria/export`

## Documentation

See [Docs](https://nonebot.dev/)

## Docker

The container image keeps the main project environment in `/app/.venv`.
User extension state stays under `/app/.apeiria`, which should be mounted.
The frontend is built into the image at build time, so the running container does
not need `node`, `pnpm`, or `npm`. Startup frontend builds are explicitly disabled
in the container.

Build and run:

```bash
docker compose up --build
```

The container command is:

```bash
APEIRIA_BUILD_FRONTEND_ON_START=false .venv/bin/apeiria init --no-dev
APEIRIA_BUILD_FRONTEND_ON_START=false .venv/bin/apeiria run
```

Mounted paths in `docker-compose.yml`:

1. `.apeiria:/app/.apeiria`
2. `data:/app/data`
3. `apeiria.config.toml:/app/apeiria.config.toml`
4. `apeiria.plugins.toml:/app/apeiria.plugins.toml`
5. `apeiria.adapters.toml:/app/apeiria.adapters.toml`
6. `apeiria.drivers.toml:/app/apeiria.drivers.toml`
7. `.env:/app/.env`
8. `.env.dev:/app/.env.dev`
9. `.env.prod:/app/.env.prod`

That means Docker keeps:

1. extension environment in `.apeiria/extensions/`
2. uv cache in `.apeiria/cache/`
3. root runtime config files in `apeiria.*.toml`
4. environment files in `.env*`

The bind-mounted `apeiria.*.toml` files must exist on the host before `docker compose up`.
Missing `.env*` files can be created by `apeiria init`, including the container startup
command, as empty files.

The compose service also sets `HOST=0.0.0.0`, so the Web UI is reachable from the
host on `http://127.0.0.1:8080/`.

If you need to install user plugins inside the container:

```bash
docker compose exec apeiria /app/.venv/bin/apeiria plugin install <package>
docker compose exec apeiria /app/.venv/bin/apeiria adapter install <package>
docker compose exec apeiria /app/.venv/bin/apeiria driver install <package>
```
