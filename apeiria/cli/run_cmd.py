from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from apeiria.bootstrap.plan import BootstrapPlan
from apeiria.bootstrap.steps import (
    step_access,
    step_apeiria_ensure,
    step_apeiria_inject,
    step_apeiria_sync,
    step_conversation,
    step_db_migrate,
    step_db_shutdown,
    step_load_adapters,
    step_load_builtin_adapters,
    step_load_builtins,
    step_load_local,
    step_load_pypi,
    step_web,
    step_webchat,
)
from apeiria.config.loader import expand_config, load_config
from apeiria.db.engine import init_db
from apeiria.db.url import build_db_url

GRACEFUL_SHUTDOWN_TIMEOUT = 3


@click.command("run")
@click.option("--reload", is_flag=True, default=False, help="Enable hot reload")
def run_cmd(reload: bool) -> None:  # noqa: FBT001
    import nonebot
    from dotenv import load_dotenv
    from nonebot.log import logger

    from apeiria.web.logs import get_log_hub

    load_dotenv(".env", override=False)
    env = os.environ.get("ENVIRONMENT", "prod")
    env_file = f".env.{env}"
    if Path(env_file).exists():
        load_dotenv(env_file, override=False)

    app = load_config("data/config.yaml")
    get_log_hub().install_sinks(app.apeiria.logging)
    expand_config(app)

    nonebot.init()

    db_path = app.apeiria.database.path
    import asyncio

    asyncio.run(init_db(build_db_url(db_path)))

    plan = BootstrapPlan()
    plan.add_step("db_migrate", step_db_migrate)
    plan.add_step("db_shutdown", step_db_shutdown)
    plan.add_step("apeiria_ensure", step_apeiria_ensure)
    plan.add_step("apeiria_sync", step_apeiria_sync, depends=["apeiria_ensure"])
    plan.add_step("apeiria_inject", step_apeiria_inject, depends=["apeiria_sync"])
    plan.add_step(
        "load_builtin_adapters",
        step_load_builtin_adapters,
        depends=["apeiria_ensure"],
    )
    plan.add_step("load_adapters", step_load_adapters, depends=["apeiria_inject"])
    plan.add_step(
        "load_builtins",
        step_load_builtins,
        depends=["load_adapters", "load_builtin_adapters"],
    )
    plan.add_step(
        "load_local",
        step_load_local,
        depends=["load_adapters", "load_builtin_adapters"],
    )
    plan.add_step(
        "load_pypi",
        step_load_pypi,
        depends=["load_adapters", "load_builtin_adapters"],
    )
    plan.add_step(
        "conversation",
        step_conversation,
        depends=["load_builtins", "load_local"],
    )
    plan.add_step("access", step_access, depends=["load_builtins", "load_local"])
    plan.add_step("webchat", step_webchat, depends=["conversation", "access"])
    plan.add_step("web", step_web, depends=["access", "webchat"])

    result = plan.run("full")
    if not result.ok:
        logger.error(
            "Bootstrap failed: {} step(s) failed: {}",
            len(result.failed),
            ", ".join(result.failed),
        )
        sys.exit(1)

    if reload:
        import threading

        import watchfiles

        def _watch_and_restart() -> None:
            for _changes in watchfiles.watch(
                Path("apeiria"),
                Path(".apeiria/plugins"),
                Path("data/config.yaml"),
                Path("webui/src"),
                Path("alembic"),
            ):
                click.echo("Changes detected — restarting...")
                sys.stdout.flush()
                sys.stderr.flush()
                os.execv(sys.executable, [sys.executable, *sys.argv])

        click.echo("Hot reload enabled — watching for changes...")
        threading.Thread(target=_watch_and_restart, daemon=True).start()
        nonebot.run(timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_TIMEOUT)
    else:
        nonebot.run(timeout_graceful_shutdown=GRACEFUL_SHUTDOWN_TIMEOUT)
