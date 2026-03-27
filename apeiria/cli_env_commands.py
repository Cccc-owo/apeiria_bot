from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

from apeiria.cli_i18n import _
from apeiria.core.utils.webui_build import write_frontend_build_meta
from apeiria.runtime_env import (
    ensure_plugin_project,
    find_uv_executable,
    plugin_project_exists,
    plugin_project_lock_path,
    plugin_project_pyproject_path,
    plugin_project_root,
    sync_plugin_project,
    uv_cache_dir,
)


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_uv_for_project(*args: str) -> None:
    executable = find_uv_executable()
    cache_dir = uv_cache_dir()
    root = project_root()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(cache_dir)
    env["UV_PROJECT_ENVIRONMENT"] = str(root / ".venv")
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        [executable, *args],
        cwd=root,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise click.ClickException(_("uv command failed"))


def sync_main_project(*, no_dev: bool = False) -> None:
    args = ["sync"]
    if (project_root() / "uv.lock").exists():
        args.append("--locked")
    if no_dev:
        args.append("--no-dev")
    run_uv_for_project(*args)


def ensure_empty_file(target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")


def ensure_runtime_env_files() -> None:
    root = project_root()
    ensure_empty_file(root / ".env")
    ensure_empty_file(root / ".env.dev")
    ensure_empty_file(root / ".env.prod")


def initialize_user_environment(*, no_dev: bool = False) -> None:
    ensure_runtime_env_files()
    sync_main_project(no_dev=no_dev)
    ensure_plugin_project()
    sync_plugin_project(locked=True)


def repair_user_environment() -> None:
    initialize_user_environment()


def raise_click_runtime_error(exc: RuntimeError) -> None:
    raise click.ClickException(str(exc)) from exc


def runtime_export_targets() -> list[tuple[Path, Path]]:
    root = project_root()
    return [
        (root / "apeiria.config.toml", Path("apeiria.config.toml")),
        (root / "apeiria.plugins.toml", Path("apeiria.plugins.toml")),
        (root / "apeiria.adapters.toml", Path("apeiria.adapters.toml")),
        (root / "apeiria.drivers.toml", Path("apeiria.drivers.toml")),
        (
            plugin_project_pyproject_path(),
            Path(".apeiria/extensions/pyproject.toml"),
        ),
        (
            plugin_project_lock_path(),
            Path(".apeiria/extensions/uv.lock"),
        ),
    ]


def copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def replace_managed_file(source: Path, destination: Path) -> bool:
    if not source.exists():
        if destination.exists():
            destination.unlink()
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def check_system_dependencies() -> None:
    missing: list[str] = []
    if shutil.which("uv") is None:
        missing.append("uv")
    if missing:
        raise click.ClickException(
            _("missing system dependencies: {deps}").format(deps=", ".join(missing))
        )

    web_dir = project_root() / "web"
    needs_frontend_toolchain = (web_dir / "package.json").is_file() and not (
        web_dir / "dist"
    ).is_dir()
    frontend_missing: list[str] = []
    if needs_frontend_toolchain:
        if shutil.which("node") is None:
            frontend_missing.append("node")
        if shutil.which("pnpm") is None and shutil.which("npm") is None:
            frontend_missing.append("pnpm-or-npm")
    if frontend_missing:
        click.echo(
            _("frontend toolchain missing: {deps}").format(
                deps=", ".join(frontend_missing)
            ),
            err=True,
        )


def build_frontend() -> None:
    web_dir = project_root() / "web"
    if not (web_dir / "package.json").is_file():
        raise click.ClickException(_("frontend workspace not found"))
    if shutil.which("node") is None:
        raise click.ClickException(
            _("frontend toolchain missing: {deps}").format(deps="node")
        )

    if shutil.which("pnpm") is not None:
        build_cmd = ["pnpm", "build"]
    elif shutil.which("npm") is not None:
        build_cmd = ["npm", "run", "build"]
    else:
        raise click.ClickException(
            _("frontend toolchain missing: {deps}").format(deps="pnpm-or-npm")
        )

    result = subprocess.run(build_cmd, cwd=web_dir, check=False)
    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)
    write_frontend_build_meta(project_root())


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_("Inspect and migrate Apeiria environments."),
)
def env() -> None:
    """Inspect and migrate Apeiria environments."""


@env.command("init", help=_("Initialize Apeiria user environment with uv."))
@click.option(
    "--no-dev",
    is_flag=True,
    help=_("Sync the main project environment without development dependencies."),
)
def env_init(*, no_dev: bool) -> None:
    check_system_dependencies()
    try:
        initialize_user_environment(no_dev=no_dev)
    except RuntimeError as exc:
        raise_click_runtime_error(exc)
    click.echo(_("initialized environment"))


@env.command("repair", help=_("Repair Apeiria user environment with uv."))
def env_repair() -> None:
    check_system_dependencies()
    try:
        repair_user_environment()
    except RuntimeError as exc:
        raise_click_runtime_error(exc)
    click.echo(_("repaired environment"))


@click.command(help=_("Initialize Apeiria user environment with uv."), hidden=True)
@click.option(
    "--no-dev",
    is_flag=True,
    help=_("Sync the main project environment without development dependencies."),
)
def init(*, no_dev: bool) -> None:
    env_init.callback(no_dev=no_dev)


@click.command(help=_("Repair Apeiria user environment with uv."), hidden=True)
def repair() -> None:
    env_repair.callback()


@click.command(help=_("Run bot.py with the current project Python environment."))
@click.option(
    "--build",
    "build_frontend_first",
    is_flag=True,
    help=_("Build Web UI frontend assets before running the bot."),
)
@click.argument("extra_args", nargs=-1)
def run(*, build_frontend_first: bool, extra_args: tuple[str, ...]) -> None:
    if build_frontend_first:
        build_frontend()
    result = subprocess.run(
        [sys.executable, "bot.py", *extra_args],
        cwd=project_root(),
        check=False,
    )
    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)


@env.command("info", help=_("Show current Apeiria environment paths and status."))
def env_info() -> None:
    root = project_root()
    plugin_root = plugin_project_root()
    lines = [
        f"project_root={root}",
        f"uv_available={shutil.which('uv') is not None}",
        f"node_available={shutil.which('node') is not None}",
        f"pnpm_available={shutil.which('pnpm') is not None}",
        f"npm_available={shutil.which('npm') is not None}",
        f"main_lock_exists={(root / 'uv.lock').exists()}",
        f"plugin_project={plugin_root}",
        f"plugin_project_exists={plugin_project_exists()}",
        f"plugin_lock_exists={plugin_project_lock_path().exists()}",
        f"plugin_config_exists={(root / 'apeiria.plugins.toml').exists()}",
        f"adapter_config_exists={(root / 'apeiria.adapters.toml').exists()}",
        f"driver_config_exists={(root / 'apeiria.drivers.toml').exists()}",
    ]
    for line in lines:
        click.echo(line)


@env.command("export", help=_("Export local runtime state for migration."))
@click.argument("output_dir", required=False)
def env_export(output_dir: str | None) -> None:
    target_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else (project_root() / ".apeiria" / "export").resolve()
    )
    copied = 0
    for source, relative_path in runtime_export_targets():
        if copy_if_exists(source, target_root / relative_path):
            copied += 1
    click.echo(_("exported files: {count}").format(count=copied))
    click.echo(_("export target: {target}").format(target=target_root))


@env.command("import", help=_("Import local runtime state from a migration bundle."))
@click.argument("input_dir")
def env_import(input_dir: str) -> None:
    source_root = Path(input_dir).expanduser().resolve()
    if not source_root.is_dir():
        raise click.ClickException(
            _("import source not found: {path}").format(path=source_root)
        )
    copied = 0
    for destination, relative_path in runtime_export_targets():
        source = source_root / relative_path
        if replace_managed_file(source, destination):
            copied += 1
    try:
        initialize_user_environment()
    except RuntimeError as exc:
        raise_click_runtime_error(exc)
    click.echo(_("imported files: {count}").format(count=copied))
