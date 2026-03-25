# apeiria_bot

## Environment Setup

This project uses `uv` to manage two environments:

1. the main project environment in `.venv`
2. the user extension environment in `.apeiria/extensions/.venv`

Before initialization, make sure the machine has:

1. Python 3.10+
2. `uv`
3. `node` and `pnpm` or `npm` if Web UI assets need to build on first start

Some plugins may still require extra system libraries depending on the platform.

## How to start

1. clone the repository
2. install project environment using `uv sync --locked`
3. activate the virtual environment
4. POSIX shells: `source .venv/bin/activate`
5. initialize the project and user extension environments using `apeiria init`
6. install user plugins using `apeiria plugin install <package>`
7. run your bot using `apeiria run`

## Environment Management

After activating `.venv`, use these commands:

1. `apeiria init`
   create or sync the main project environment and the user extension environment
2. `apeiria repair`
   re-sync both environments from current managed files
3. `apeiria env info`
   show current environment paths and status

Main environment responsibilities:

1. runtime for the Apeiria project itself
2. framework and built-in project dependencies

User extension environment responsibilities:

1. user-installed plugins
2. user-installed adapters
3. user-installed drivers

The extension environment is managed under `.apeiria/extensions/` and is ignored by git.

## User Packages

Use Apeiria commands to manage packages in the user extension environment:

1. `apeiria plugin install <package>`
2. `apeiria adapter install <package>`
3. `apeiria driver install <package>`

Installed user packages are declared in `.apeiria/extensions/pyproject.toml`.
Their project registrations remain in:

1. `apeiria.plugins.toml`
2. `apeiria.adapters.toml`
3. `apeiria.drivers.toml`

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
