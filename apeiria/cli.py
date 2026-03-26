from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import click

from apeiria.cli_i18n import _
from apeiria.cli_nb import (
    find_exact_store_package,
    format_store_packages,
    prompt_select_store_package,
    prompt_select_text,
    search_store_packages,
)
from apeiria.config import (
    adapter_config_service,
    driver_config_service,
    plugin_config_service,
)
from apeiria.core.plugin_policy import is_framework_protected_plugin_module
from apeiria.core.utils.webui_build import write_frontend_build_meta
from apeiria.runtime_env import (
    add_plugin_requirement,
    ensure_plugin_project,
    find_uv_executable,
    plugin_project_exists,
    plugin_project_lock_path,
    plugin_project_pyproject_path,
    plugin_project_root,
    remove_plugin_requirement,
    resolve_declared_plugin_requirement,
    sync_plugin_project,
    update_plugin_requirement,
    uv_cache_dir,
)

add_project_adapter_module = adapter_config_service.add_project_adapter_module
bind_project_adapter_package = adapter_config_service.bind_project_adapter_package
default_adapter_config_path = adapter_config_service.default_config_path
ensure_project_adapter_config = adapter_config_service.ensure_project_adapter_config
get_project_adapter_package_modules = (
    adapter_config_service.get_project_adapter_package_modules
)
read_project_adapter_config = adapter_config_service.read_project_adapter_config
remove_project_adapter_module = adapter_config_service.remove_project_adapter_module
unbind_project_adapter_package = adapter_config_service.unbind_project_adapter_package

add_project_driver_builtin = driver_config_service.add_project_driver_builtin
bind_project_driver_package = driver_config_service.bind_project_driver_package
default_driver_config_path = driver_config_service.default_config_path
ensure_project_driver_config = driver_config_service.ensure_project_driver_config
get_project_driver_kwargs = driver_config_service.get_project_driver_kwargs
get_project_driver_package_builtin = (
    driver_config_service.get_project_driver_package_builtin
)
read_project_driver_config = driver_config_service.read_project_driver_config
remove_project_driver_builtin = driver_config_service.remove_project_driver_builtin
unbind_project_driver_package = driver_config_service.unbind_project_driver_package

add_project_plugin_dir = plugin_config_service.add_project_plugin_dir
add_project_plugin_module = plugin_config_service.add_project_plugin_module
bind_project_plugin_package = plugin_config_service.bind_project_plugin_package
default_plugin_config_path = plugin_config_service.default_config_path
ensure_project_plugin_config = plugin_config_service.ensure_project_plugin_config
get_project_plugin_package_modules = (
    plugin_config_service.get_project_plugin_package_modules
)
read_project_plugin_config = plugin_config_service.read_project_plugin_config
remove_project_plugin_dir = plugin_config_service.remove_project_plugin_dir
remove_project_plugin_module = plugin_config_service.remove_project_plugin_module
unbind_project_plugin_package = plugin_config_service.unbind_project_plugin_package


def _config_path(path: str | None) -> Path | None:
    return Path(path).expanduser().resolve() if path else None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _current_config_path(config_path: Path | None, default_path: Path) -> Path:
    return default_path if config_path is None else config_path


def _normalize_module_name(name: str) -> str:
    base = name.split("[", 1)[0].strip()
    return base.replace("-", "_")


def _echo_config(config_path: Path | None) -> None:
    config = read_project_plugin_config(config_path)
    current_path = _current_config_path(config_path, default_plugin_config_path())
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("modules:"))
    for module in config["modules"]:
        click.echo(f"  - {module}")
    click.echo(_("dirs:"))
    for directory in config["dirs"]:
        click.echo(f"  - {directory}")


def _echo_installed_plugins(query: str | None = None) -> None:
    config = read_project_plugin_config()
    packages = sorted(config["packages"].items())
    if query:
        needle = query.lower()
        packages = [
            item
            for item in packages
            if needle in item[0].lower()
            or any(needle in module.lower() for module in item[1])
        ]
    if not packages:
        click.echo(_("no installed plugin packages found"))
        return
    click.echo(_("installed:"))
    modules_label = _("modules:")
    for name, modules in packages:
        click.echo(f"  - {name}")
        click.echo(f"    {modules_label} {', '.join(modules)}")


def _installed_plugin_package_names() -> list[str]:
    return sorted(read_project_plugin_config()["packages"])


def _echo_registered_plugins(
    config_path: Path | None, query: str | None = None
) -> None:
    config = read_project_plugin_config(config_path)
    current_path = _current_config_path(config_path, default_plugin_config_path())
    needle = (query or "").lower()
    modules = (
        [item for item in config["modules"] if needle in item.lower()]
        if needle
        else config["modules"]
    )
    dirs = (
        [item for item in config["dirs"] if needle in item.lower()]
        if needle
        else config["dirs"]
    )
    click.echo(_("registered:"))
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("modules:"))
    for module in modules:
        click.echo(f"  - {module}")
    click.echo(_("dirs:"))
    for directory in dirs:
        click.echo(f"  - {directory}")


def _echo_adapter_config(config_path: Path | None) -> None:
    config = read_project_adapter_config(config_path)
    current_path = _current_config_path(config_path, default_adapter_config_path())
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("modules:"))
    for module in config["modules"]:
        click.echo(f"  - {module}")


def _echo_driver_config(config_path: Path | None) -> None:
    config = read_project_driver_config(config_path)
    current_path = _current_config_path(config_path, default_driver_config_path())
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("builtin:"))
    for item in config["builtin"]:
        click.echo(f"  - {item}")


def _echo_installed_drivers(query: str | None = None) -> None:
    config = read_project_driver_config()
    packages = sorted(config["packages"].items())
    if query:
        needle = query.lower()
        packages = [
            item
            for item in packages
            if needle in item[0].lower()
            or any(needle in builtin.lower() for builtin in item[1])
        ]
    if not packages:
        click.echo(_("no installed driver packages found"))
        return
    click.echo(_("installed:"))
    builtin_label = _("builtin:")
    for name, builtin in packages:
        click.echo(f"  - {name}")
        click.echo(f"    {builtin_label} {', '.join(builtin)}")


def _installed_driver_package_names() -> list[str]:
    return sorted(read_project_driver_config()["packages"])


def _echo_installed_adapters(query: str | None = None) -> None:
    config = read_project_adapter_config()
    packages = sorted(config["packages"].items())
    if query:
        needle = query.lower()
        packages = [
            item
            for item in packages
            if needle in item[0].lower()
            or any(needle in module.lower() for module in item[1])
        ]
    if not packages:
        click.echo(_("no installed adapter packages found"))
        return
    click.echo(_("installed:"))
    modules_label = _("modules:")
    for name, modules in packages:
        click.echo(f"  - {name}")
        click.echo(f"    {modules_label} {', '.join(modules)}")


def _installed_adapter_package_names() -> list[str]:
    return sorted(read_project_adapter_config()["packages"])


def _echo_registered_adapters(
    config_path: Path | None, query: str | None = None
) -> None:
    config = read_project_adapter_config(config_path)
    current_path = _current_config_path(config_path, default_adapter_config_path())
    needle = (query or "").lower()
    modules = (
        [item for item in config["modules"] if needle in item.lower()]
        if needle
        else config["modules"]
    )
    click.echo(_("registered:"))
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("modules:"))
    for module in modules:
        click.echo(f"  - {module}")


def _fail(message: str) -> None:
    raise click.ClickException(message)


def _prompt_package_name(question: str, packages: list[str]) -> str:
    if not packages:
        raise click.ClickException(_("no installed packages available"))
    try:
        return prompt_select_text(question, packages)
    except RuntimeError as exc:
        if str(exc) != "nb-cli":
            raise
    except Exception as exc:
        if exc.__class__.__name__ == "CancelledError":
            raise click.Abort from exc
        raise
    click.echo(_("installed:"))
    for index, package_name in enumerate(packages, start=1):
        click.echo(f"  {index}. {package_name}")
    selected = click.prompt(question, type=click.IntRange(1, len(packages)))
    return packages[selected - 1]


def _echo_store_packages(items: list[object]) -> None:
    if not items:
        click.echo(_("no store packages found"))
        return
    click.echo(format_store_packages(items))


def _store_packages(module_type: str, query: str | None = None) -> list[object]:
    try:
        return search_store_packages(module_type, query)
    except RuntimeError as exc:
        if str(exc) == "nb-cli":
            _fail(_("nb-cli is required for official store features"))
        raise


def _exact_store_package(module_type: str, value: str) -> object | None:
    try:
        return find_exact_store_package(module_type, value)
    except RuntimeError as exc:
        if str(exc) == "nb-cli":
            _fail(_("nb-cli is required for official store features"))
        raise


def _select_store_package(module_type: str, query: str | None = None) -> object:
    try:
        return prompt_select_store_package(
            module_type,
            _("choose package"),
            query,
        )
    except RuntimeError as exc:
        if str(exc) == "nb-cli":
            _fail(_("nb-cli is required for official store features"))
        if str(exc) == "empty-store":
            _fail(_("no store packages found"))
        _fail(str(exc))
        raise
    except Exception as exc:
        if exc.__class__.__name__ == "CancelledError":
            raise click.Abort from exc
        raise


def _ensure_plugin_can_be_removed(module_name: str) -> None:
    if is_framework_protected_plugin_module(module_name):
        _fail(
            _("cannot remove protected plugin {module}: framework required").format(
                module=module_name
            )
        )


def _store_module_name(item: object) -> str:
    return str(getattr(item, "module_name", "")).strip()


def _store_project_link(item: object) -> str:
    return str(getattr(item, "project_link", "")).strip()


def _package_target(module_type: str, value: str) -> str:
    package = _exact_store_package(module_type, value)
    if package is None:
        return value
    project_link = _store_project_link(package)
    return project_link or value


def _declared_package_target(package_name: str) -> str:
    return resolve_declared_plugin_requirement(package_name)


def _resolve_plugin_module(
    package: object | None,
    module_name: str | None,
) -> str:
    if module_name:
        return module_name.strip()
    resolved = _store_module_name(package) if package is not None else ""
    if resolved:
        return resolved
    _fail(_("plugin module name is required when package is not from store"))
    return ""


def _resolve_adapter_module(
    package: object | None,
    module_name: str | None,
) -> str:
    if module_name:
        return module_name.strip()
    resolved = _store_module_name(package) if package is not None else ""
    if resolved:
        return resolved
    _fail(_("adapter module name is required when package is not from store"))
    return ""


def _resolve_driver_builtin(
    package: object | None,
    builtin_name: str | None,
) -> str:
    if builtin_name:
        return builtin_name.strip()
    resolved = _store_module_name(package) if package is not None else ""
    if resolved:
        return resolved
    _fail(_("driver builtin name is required when package is not from store"))
    return ""


def _run_uv_for_project(*args: str) -> None:
    executable = find_uv_executable()
    cache_dir = uv_cache_dir()
    project_root = _project_root()
    cache_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = str(cache_dir)
    env["UV_PROJECT_ENVIRONMENT"] = str(project_root / ".venv")
    env.pop("VIRTUAL_ENV", None)
    result = subprocess.run(
        [executable, *args],
        cwd=project_root,
        check=False,
        env=env,
    )
    if result.returncode != 0:
        raise click.ClickException(_("uv command failed"))


def _sync_main_project(*, no_dev: bool = False) -> None:
    args = ["sync"]
    if (_project_root() / "uv.lock").exists():
        args.append("--locked")
    if no_dev:
        args.append("--no-dev")
    _run_uv_for_project(*args)


def _ensure_empty_file(target: Path) -> None:
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")


def _ensure_runtime_env_files() -> None:
    project_root = _project_root()
    _ensure_empty_file(project_root / ".env")
    _ensure_empty_file(project_root / ".env.dev")
    _ensure_empty_file(project_root / ".env.prod")


def _initialize_user_environment(*, no_dev: bool = False) -> None:
    _ensure_runtime_env_files()
    _sync_main_project(no_dev=no_dev)
    ensure_plugin_project()
    sync_plugin_project(locked=True)


def _repair_user_environment() -> None:
    _initialize_user_environment()


def _raise_click_runtime_error(exc: RuntimeError) -> None:
    raise click.ClickException(str(exc)) from exc


def _rollback_failure_message(exc: Exception, detail: str) -> str:
    return f"{exc}\n{detail}"


def _rollback_install_failure_detail(target: str) -> str:
    return f"rollback failed: {target} is still installed in the extension environment"


def _rollback_uninstall_failure_detail(target: str) -> str:
    return f"rollback failed: {target} was removed from the extension environment"


def _rollback_install(
    target: str,
    pip_args: tuple[str, ...],
    exc: Exception,
) -> None:
    try:
        remove_plugin_requirement(target, pip_args)
    except RuntimeError:
        _fail(
            _rollback_failure_message(
                exc,
                _rollback_install_failure_detail(target),
            )
        )
    raise click.ClickException(str(exc)) from exc


def _rollback_uninstall(
    target: str,
    pip_args: tuple[str, ...],
    exc: Exception,
) -> None:
    try:
        add_plugin_requirement(target, pip_args)
    except RuntimeError:
        _fail(
            _rollback_failure_message(
                exc,
                _rollback_uninstall_failure_detail(target),
            )
        )
    raise click.ClickException(str(exc)) from exc


def _runtime_export_targets() -> list[tuple[Path, Path]]:
    project_root = _project_root()
    return [
        (project_root / "apeiria.config.toml", Path("apeiria.config.toml")),
        (project_root / "apeiria.plugins.toml", Path("apeiria.plugins.toml")),
        (
            project_root / "apeiria.adapters.toml",
            Path("apeiria.adapters.toml"),
        ),
        (project_root / "apeiria.drivers.toml", Path("apeiria.drivers.toml")),
        (
            plugin_project_pyproject_path(),
            Path(".apeiria/extensions/pyproject.toml"),
        ),
        (
            plugin_project_lock_path(),
            Path(".apeiria/extensions/uv.lock"),
        ),
    ]


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _replace_managed_file(source: Path, destination: Path) -> bool:
    if not source.exists():
        if destination.exists():
            destination.unlink()
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return True


def _check_system_dependencies() -> None:
    missing: list[str] = []
    if shutil.which("uv") is None:
        missing.append("uv")

    if missing:
        _fail(_("missing system dependencies: {deps}").format(deps=", ".join(missing)))

    web_dir = _project_root() / "web"
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


def _build_frontend() -> None:
    web_dir = _project_root() / "web"
    if not (web_dir / "package.json").is_file():
        _fail(_("frontend workspace not found"))

    if shutil.which("node") is None:
        _fail(_("frontend toolchain missing: {deps}").format(deps="node"))

    build_cmd: list[str]
    if shutil.which("pnpm") is not None:
        build_cmd = ["pnpm", "build"]
    elif shutil.which("npm") is not None:
        build_cmd = ["npm", "run", "build"]
    else:
        _fail(_("frontend toolchain missing: {deps}").format(deps="pnpm-or-npm"))

    result = subprocess.run(
        build_cmd,
        cwd=web_dir,
        check=False,
    )
    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)
    write_frontend_build_meta(_project_root())


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Apeiria project tools."""


@cli.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_("Inspect and migrate Apeiria environments."),
)
def env() -> None:
    """Inspect and migrate Apeiria environments."""


@cli.command(help=_("Initialize Apeiria user environment with uv."))
@click.option(
    "--no-dev",
    is_flag=True,
    help=_("Sync the main project environment without development dependencies."),
)
def init(*, no_dev: bool) -> None:
    _check_system_dependencies()
    try:
        _initialize_user_environment(no_dev=no_dev)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("initialized environment"))


@cli.command(help=_("Repair Apeiria user environment with uv."))
def repair() -> None:
    _check_system_dependencies()
    try:
        _repair_user_environment()
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("repaired environment"))


@cli.command(help=_("Run bot.py with the current project Python environment."))
@click.option(
    "--build",
    "build_frontend",
    is_flag=True,
    help=_("Build Web UI frontend assets before running the bot."),
)
@click.argument("extra_args", nargs=-1)
def run(*, build_frontend: bool, extra_args: tuple[str, ...]) -> None:
    if build_frontend:
        _build_frontend()
    result = subprocess.run(
        [sys.executable, "bot.py", *extra_args],
        cwd=_project_root(),
        check=False,
    )
    if result.returncode != 0:
        raise click.exceptions.Exit(result.returncode)


@env.command("info", help=_("Show current Apeiria environment paths and status."))
def env_info() -> None:
    project_root = _project_root()
    plugin_root = plugin_project_root()
    lines = [
        f"project_root={project_root}",
        f"uv_available={shutil.which('uv') is not None}",
        f"node_available={shutil.which('node') is not None}",
        f"pnpm_available={shutil.which('pnpm') is not None}",
        f"npm_available={shutil.which('npm') is not None}",
        f"main_lock_exists={(project_root / 'uv.lock').exists()}",
        f"plugin_project={plugin_root}",
        f"plugin_project_exists={plugin_project_exists()}",
        f"plugin_lock_exists={plugin_project_lock_path().exists()}",
        f"plugin_config_exists={(project_root / 'apeiria.plugins.toml').exists()}",
        f"adapter_config_exists={(project_root / 'apeiria.adapters.toml').exists()}",
        f"driver_config_exists={(project_root / 'apeiria.drivers.toml').exists()}",
    ]
    for line in lines:
        click.echo(line)


@env.command("export", help=_("Export local runtime state for migration."))
@click.argument("output_dir", required=False)
def env_export(output_dir: str | None) -> None:
    target_root = (
        Path(output_dir).expanduser().resolve()
        if output_dir
        else (_project_root() / ".apeiria" / "export").resolve()
    )
    copied = 0
    for source, relative_path in _runtime_export_targets():
        if _copy_if_exists(source, target_root / relative_path):
            copied += 1
    click.echo(_("exported files: {count}").format(count=copied))
    click.echo(_("export target: {target}").format(target=target_root))


@env.command("import", help=_("Import local runtime state from a migration bundle."))
@click.argument("input_dir")
def env_import(input_dir: str) -> None:
    source_root = Path(input_dir).expanduser().resolve()
    if not source_root.is_dir():
        _fail(_("import source not found: {path}").format(path=source_root))
    copied = 0
    for destination, relative_path in _runtime_export_targets():
        source = source_root / relative_path
        if _replace_managed_file(source, destination):
            copied += 1
    try:
        _initialize_user_environment()
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("imported files: {count}").format(count=copied))


@cli.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_("Manage Apeiria project plugins."),
)
def plugin() -> None:
    """Manage Apeiria project plugins."""


@plugin.command(
    "store",
    help=_("Browse nonebot plugin store with interactive selection."),
)
@click.argument("query", required=False)
def plugin_store(query: str | None) -> None:
    item = _select_store_package("plugin", query)
    _echo_store_packages([item])


@cli.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_("Manage Apeiria project adapters."),
)
def adapter() -> None:
    """Manage Apeiria project adapters."""


@adapter.command(
    "store",
    help=_("Browse nonebot adapter store with interactive selection."),
)
@click.argument("query", required=False)
def adapter_store(query: str | None) -> None:
    item = _select_store_package("adapter", query)
    _echo_store_packages([item])


@cli.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help=_("Manage Apeiria project drivers."),
)
def driver() -> None:
    """Manage Apeiria project drivers."""


@driver.command(
    "store",
    help=_("Browse nonebot driver store with interactive selection."),
)
@click.argument("query", required=False)
def driver_store(query: str | None) -> None:
    item = _select_store_package("driver", query)
    _echo_store_packages([item])


@plugin.command(
    "init",
    help=_("Create apeiria.plugins.toml and the user plugin project if missing."),
    hidden=True,
)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def plugin_init(config_arg: str | None) -> None:
    target = ensure_project_plugin_config(_config_path(config_arg))
    plugin_root = ensure_plugin_project()
    click.echo(_("initialized: {target}").format(target=target))
    click.echo(_("initialized: {target}").format(target=plugin_root))


@plugin.command("list", help=_("List registered plugins or installed plugin packages."))
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("List installed plugin packages."))
@click.option(
    "--registered", is_flag=True, help=_("List registered plugin config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("List official store packages.")
)
def plugin_list(
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_plugins()
        return
    if registered:
        _echo_registered_plugins(_config_path(config_arg))
        return
    if use_store:
        _echo_store_packages(_store_packages("plugin"))
        return
    _echo_registered_plugins(_config_path(config_arg))
    click.echo()
    _echo_installed_plugins()


@plugin.command(
    "search",
    help=_("Search registered plugins or installed plugin packages."),
    hidden=True,
)
@click.argument("query", required=False)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("Search installed plugin packages."))
@click.option(
    "--registered", is_flag=True, help=_("Search registered plugin config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Search official store packages.")
)
def plugin_search(
    query: str | None,
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_plugins(query)
        return
    if registered:
        _echo_registered_plugins(_config_path(config_arg), query)
        return
    if use_store:
        _echo_store_packages(_store_packages("plugin", query))
        return
    _echo_registered_plugins(_config_path(config_arg), query)
    click.echo()
    _echo_installed_plugins(query)


@plugin.command(
    "register",
    help=_("Register a plugin module in apeiria.plugins.toml."),
    hidden=True,
)
@click.argument("module_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def plugin_register(module_name: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_plugin_config(config_path)
    add_project_plugin_module(module_name, config_path)
    click.echo(_("registered module: {module}").format(module=module_name))
    _echo_config(config_path)


@plugin.command(
    "unregister",
    help=_("Remove a plugin module from apeiria.plugins.toml."),
    hidden=True,
)
@click.argument("module_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def plugin_unregister(module_name: str, config_arg: str | None) -> None:
    _ensure_plugin_can_be_removed(module_name)
    config_path = _config_path(config_arg)
    ensure_project_plugin_config(config_path)
    remove_project_plugin_module(module_name, config_path)
    click.echo(_("unregistered module: {module}").format(module=module_name))
    _echo_config(config_path)


@plugin.command(
    "install",
    context_settings={"ignore_unknown_options": True},
    help=_("Install a plugin package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--module",
    "module_name",
    help=_("Plugin module name to register when store metadata is unavailable."),
)
def plugin_install(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    module_name: str | None,
) -> None:
    package = (
        _select_store_package("plugin", package_name)
        if use_store or not package_name
        else _exact_store_package("plugin", package_name)
    )
    target = package.as_dependency() if package else package_name
    if not target:
        _fail(_("package name is required"))
    resolved_module = _resolve_plugin_module(package, module_name)
    try:
        add_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        bind_project_plugin_package(target, resolved_module)
    except Exception as exc:  # noqa: BLE001
        _rollback_install(target, pip_args, exc)
    click.echo(_("installed package: {package}").format(package=target))


@plugin.command("add", context_settings={"ignore_unknown_options": True}, hidden=True)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--module",
    "module_name",
    help=_("Plugin module name to register when store metadata is unavailable."),
)
def plugin_add(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    module_name: str | None,
) -> None:
    plugin_install(package_name, pip_args, use_store=use_store, module_name=module_name)


@plugin.command(
    "update",
    context_settings={"ignore_unknown_options": True},
    help=_("Update a plugin package with current environment manager."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
def plugin_update(package_name: str | None, pip_args: tuple[str, ...]) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_plugin_package_names(),
    )
    target = _declared_package_target(selected_package)
    try:
        update_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("updated package: {package}").format(package=target))


@plugin.command(
    "uninstall",
    context_settings={"ignore_unknown_options": True},
    help=_("Uninstall a plugin package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--module",
    "module_name",
    help=_("Plugin module name to unregister when package metadata is unavailable."),
)
def plugin_uninstall(
    package_name: str | None,
    pip_args: tuple[str, ...],
    module_name: str | None,
) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_plugin_package_names(),
    )
    target = _declared_package_target(selected_package)
    registered_modules = get_project_plugin_package_modules(target)
    if not registered_modules:
        registered_module = module_name.strip() if module_name else ""
        if not registered_module:
            package = _exact_store_package("plugin", selected_package)
            registered_module = (
                _store_module_name(package) if package is not None else ""
            )
        if not registered_module:
            _fail(_("plugin module name is required when package is not from store"))
        registered_modules = [registered_module]
    for registered_module in registered_modules:
        _ensure_plugin_can_be_removed(registered_module)
    try:
        remove_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        if get_project_plugin_package_modules(target):
            unbind_project_plugin_package(target)
        else:
            for registered_module in registered_modules:
                remove_project_plugin_module(registered_module)
    except Exception as exc:  # noqa: BLE001
        _rollback_uninstall(target, pip_args, exc)
    click.echo(_("uninstalled package: {package}").format(package=target))


@plugin.command(
    "remove",
    context_settings={"ignore_unknown_options": True},
    hidden=True,
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--module",
    "module_name",
    help=_("Plugin module name to unregister when package metadata is unavailable."),
)
def plugin_remove(
    package_name: str | None,
    pip_args: tuple[str, ...],
    module_name: str | None,
) -> None:
    plugin_uninstall(package_name, pip_args, module_name)


@plugin.command(
    "add-dir",
    help=_("Register a plugin directory in apeiria.plugins.toml."),
    hidden=True,
)
@click.argument("directory")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def plugin_add_dir(directory: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_plugin_config(config_path)
    add_project_plugin_dir(directory, config_path)
    click.echo(_("added dir: {directory}").format(directory=directory))
    _echo_config(config_path)


@plugin.command(
    "remove-dir",
    help=_("Remove a plugin directory from apeiria.plugins.toml."),
    hidden=True,
)
@click.argument("directory")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def plugin_remove_dir(directory: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_plugin_config(config_path)
    remove_project_plugin_dir(directory, config_path)
    click.echo(_("removed dir: {directory}").format(directory=directory))
    _echo_config(config_path)


@adapter.command(
    "init",
    help=_("Create apeiria.adapters.toml if it does not exist."),
    hidden=True,
)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def adapter_init(config_arg: str | None) -> None:
    target = ensure_project_adapter_config(_config_path(config_arg))
    click.echo(_("initialized: {target}").format(target=target))


@adapter.command(
    "list", help=_("List registered adapters or installed adapter packages.")
)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("List installed adapter packages."))
@click.option(
    "--registered", is_flag=True, help=_("List registered adapter config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("List official store packages.")
)
def adapter_list(
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_adapters()
        return
    if registered:
        _echo_registered_adapters(_config_path(config_arg))
        return
    if use_store:
        _echo_store_packages(_store_packages("adapter"))
        return
    _echo_registered_adapters(_config_path(config_arg))
    click.echo()
    _echo_installed_adapters()


@adapter.command(
    "search",
    help=_("Search registered adapters or installed adapter packages."),
    hidden=True,
)
@click.argument("query", required=False)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("Search installed adapter packages."))
@click.option(
    "--registered", is_flag=True, help=_("Search registered adapter config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Search official store packages.")
)
def adapter_search(
    query: str | None,
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_adapters(query)
        return
    if registered:
        _echo_registered_adapters(_config_path(config_arg), query)
        return
    if use_store:
        _echo_store_packages(_store_packages("adapter", query))
        return
    _echo_registered_adapters(_config_path(config_arg), query)
    click.echo()
    _echo_installed_adapters(query)


@adapter.command(
    "register",
    help=_("Register an adapter module in apeiria.adapters.toml."),
    hidden=True,
)
@click.argument("module_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def adapter_register(module_name: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_adapter_config(config_path)
    add_project_adapter_module(module_name, config_path)
    click.echo(_("registered module: {module}").format(module=module_name))
    _echo_adapter_config(config_path)


@adapter.command(
    "unregister",
    help=_("Remove an adapter module from apeiria.adapters.toml."),
    hidden=True,
)
@click.argument("module_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def adapter_unregister(module_name: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_adapter_config(config_path)
    remove_project_adapter_module(module_name, config_path)
    click.echo(_("unregistered module: {module}").format(module=module_name))
    _echo_adapter_config(config_path)


@adapter.command(
    "install",
    context_settings={"ignore_unknown_options": True},
    help=_("Install an adapter package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--module",
    "module_name",
    help=_("Adapter module name to register when store metadata is unavailable."),
)
def adapter_install(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    module_name: str | None,
) -> None:
    package = (
        _select_store_package("adapter", package_name)
        if use_store or not package_name
        else _exact_store_package("adapter", package_name)
    )
    target = package.as_dependency() if package else package_name
    if not target:
        _fail(_("package name is required"))
    resolved_module = _resolve_adapter_module(package, module_name)
    try:
        add_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        bind_project_adapter_package(target, resolved_module)
    except Exception as exc:  # noqa: BLE001
        _rollback_install(target, pip_args, exc)
    click.echo(_("installed package: {package}").format(package=target))


@adapter.command("add", context_settings={"ignore_unknown_options": True}, hidden=True)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--module",
    "module_name",
    help=_("Adapter module name to register when store metadata is unavailable."),
)
def adapter_add(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    module_name: str | None,
) -> None:
    adapter_install(
        package_name,
        pip_args,
        use_store=use_store,
        module_name=module_name,
    )


@adapter.command(
    "update",
    context_settings={"ignore_unknown_options": True},
    help=_("Update an adapter package with current environment manager."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
def adapter_update(package_name: str | None, pip_args: tuple[str, ...]) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_adapter_package_names(),
    )
    target = _declared_package_target(selected_package)
    try:
        update_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("updated package: {package}").format(package=target))


@adapter.command(
    "uninstall",
    context_settings={"ignore_unknown_options": True},
    help=_("Uninstall an adapter package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--module",
    "module_name",
    help=_("Adapter module name to unregister when package metadata is unavailable."),
)
def adapter_uninstall(
    package_name: str | None,
    pip_args: tuple[str, ...],
    module_name: str | None,
) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_adapter_package_names(),
    )
    target = _declared_package_target(selected_package)
    registered_modules = get_project_adapter_package_modules(target)
    if not registered_modules:
        registered_module = module_name.strip() if module_name else ""
        if not registered_module:
            package = _exact_store_package("adapter", selected_package)
            registered_module = (
                _store_module_name(package) if package is not None else ""
            )
        if not registered_module:
            _fail(_("adapter module name is required when package is not from store"))
        registered_modules = [registered_module]
    try:
        remove_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        if get_project_adapter_package_modules(target):
            unbind_project_adapter_package(target)
        else:
            for registered_module in registered_modules:
                remove_project_adapter_module(registered_module)
    except Exception as exc:  # noqa: BLE001
        _rollback_uninstall(target, pip_args, exc)
    click.echo(_("uninstalled package: {package}").format(package=target))


@adapter.command(
    "remove",
    context_settings={"ignore_unknown_options": True},
    hidden=True,
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--module",
    "module_name",
    help=_("Adapter module name to unregister when package metadata is unavailable."),
)
def adapter_remove(
    package_name: str | None,
    pip_args: tuple[str, ...],
    module_name: str | None,
) -> None:
    adapter_uninstall(package_name, pip_args, module_name)


@driver.command(
    "init",
    help=_("Create apeiria.drivers.toml if it does not exist."),
    hidden=True,
)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def driver_init(config_arg: str | None) -> None:
    target = ensure_project_driver_config(_config_path(config_arg))
    click.echo(_("initialized: {target}").format(target=target))


@driver.command("list", help=_("List registered drivers or installed driver packages."))
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("List installed driver packages."))
@click.option(
    "--registered", is_flag=True, help=_("List registered driver config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("List official store packages.")
)
def driver_list(
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_drivers()
        return
    if registered:
        _echo_driver_config(_config_path(config_arg))
        return
    if use_store:
        _echo_store_packages(_store_packages("driver"))
        return
    _echo_driver_config(_config_path(config_arg))
    click.echo()
    _echo_installed_drivers()


@driver.command(
    "search",
    help=_("Search registered drivers or installed driver packages."),
    hidden=True,
)
@click.argument("query", required=False)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
@click.option("--installed", is_flag=True, help=_("Search installed driver packages."))
@click.option(
    "--registered", is_flag=True, help=_("Search registered driver config only.")
)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Search official store packages.")
)
def driver_search(
    query: str | None,
    config_arg: str | None,
    *,
    installed: bool,
    registered: bool,
    use_store: bool,
) -> None:
    if sum([installed, registered, use_store]) > 1:
        _fail(_("--installed, --registered and --store cannot be used together"))
    if installed:
        _echo_installed_drivers(query)
        return
    if registered:
        config = read_project_driver_config(_config_path(config_arg))
    else:
        config = read_project_driver_config(_config_path(config_arg))
    if use_store:
        _echo_store_packages(_store_packages("driver", query))
        return
    needle = (query or "").lower()
    filtered_builtin = (
        [item for item in config["builtin"] if needle in item.lower()]
        if needle
        else config["builtin"]
    )
    current_path = _current_config_path(
        _config_path(config_arg),
        default_driver_config_path(),
    )
    click.echo(_("config: {path}").format(path=current_path))
    click.echo(_("builtin:"))
    for item in filtered_builtin:
        click.echo(f"  - {item}")
    if not registered:
        click.echo()
        _echo_installed_drivers(query)


@driver.command(
    "install",
    context_settings={"ignore_unknown_options": True},
    help=_("Install a driver package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--builtin",
    "builtin_name",
    help=_("Driver builtin name to register when store metadata is unavailable."),
)
def driver_install(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    builtin_name: str | None,
) -> None:
    package = (
        _select_store_package("driver", package_name)
        if use_store or not package_name
        else _exact_store_package("driver", package_name)
    )
    target = package.as_dependency() if package else package_name
    if not target:
        _fail(_("package name is required"))
    resolved_builtin = _resolve_driver_builtin(package, builtin_name)
    try:
        add_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        bind_project_driver_package(target, resolved_builtin)
    except Exception as exc:  # noqa: BLE001
        _rollback_install(target, pip_args, exc)
    click.echo(_("installed package: {package}").format(package=target))


@driver.command("add", context_settings={"ignore_unknown_options": True}, hidden=True)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--store", "use_store", is_flag=True, help=_("Choose from official store.")
)
@click.option(
    "--builtin",
    "builtin_name",
    help=_("Driver builtin name to register when store metadata is unavailable."),
)
def driver_add(
    package_name: str | None,
    pip_args: tuple[str, ...],
    *,
    use_store: bool,
    builtin_name: str | None,
) -> None:
    driver_install(
        package_name,
        pip_args,
        use_store=use_store,
        builtin_name=builtin_name,
    )


@driver.command(
    "update",
    context_settings={"ignore_unknown_options": True},
    help=_("Update a driver package with current environment manager."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
def driver_update(package_name: str | None, pip_args: tuple[str, ...]) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_driver_package_names(),
    )
    target = _declared_package_target(selected_package)
    try:
        update_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    click.echo(_("updated package: {package}").format(package=target))


@driver.command(
    "uninstall",
    context_settings={"ignore_unknown_options": True},
    help=_("Uninstall a driver package."),
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--builtin",
    "builtin_name",
    help=_("Driver builtin name to unregister when package metadata is unavailable."),
)
def driver_uninstall(
    package_name: str | None,
    pip_args: tuple[str, ...],
    builtin_name: str | None,
) -> None:
    selected_package = package_name or _prompt_package_name(
        _("choose package"),
        _installed_driver_package_names(),
    )
    target = _declared_package_target(selected_package)
    registered_builtin = get_project_driver_package_builtin(target)
    if not registered_builtin:
        resolved_builtin = builtin_name.strip() if builtin_name else ""
        if not resolved_builtin:
            package = _exact_store_package("driver", selected_package)
            resolved_builtin = (
                _store_module_name(package) if package is not None else ""
            )
        if not resolved_builtin:
            _fail(_("driver builtin name is required when package is not from store"))
        registered_builtin = [resolved_builtin]
    try:
        remove_plugin_requirement(target, pip_args)
    except RuntimeError as exc:
        _raise_click_runtime_error(exc)
    try:
        if get_project_driver_package_builtin(target):
            unbind_project_driver_package(target)
        else:
            for item in registered_builtin:
                remove_project_driver_builtin(item)
    except Exception as exc:  # noqa: BLE001
        _rollback_uninstall(target, pip_args, exc)
    click.echo(_("uninstalled package: {package}").format(package=target))


@driver.command(
    "remove",
    context_settings={"ignore_unknown_options": True},
    hidden=True,
)
@click.argument("package_name", required=False)
@click.argument("pip_args", nargs=-1)
@click.option(
    "--builtin",
    "builtin_name",
    help=_("Driver builtin name to unregister when package metadata is unavailable."),
)
def driver_remove(
    package_name: str | None,
    pip_args: tuple[str, ...],
    builtin_name: str | None,
) -> None:
    driver_uninstall(package_name, pip_args, builtin_name)


@driver.command(
    "register",
    help=_("Register a built-in driver entry in apeiria.drivers.toml."),
    hidden=True,
)
@click.argument("builtin_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def driver_register(builtin_name: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_driver_config(config_path)
    add_project_driver_builtin(builtin_name, config_path)
    click.echo(_("registered builtin: {builtin}").format(builtin=builtin_name))
    _echo_driver_config(config_path)


@driver.command(
    "unregister",
    help=_("Remove a built-in driver entry from apeiria.drivers.toml."),
    hidden=True,
)
@click.argument("builtin_name")
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def driver_unregister(builtin_name: str, config_arg: str | None) -> None:
    config_path = _config_path(config_arg)
    ensure_project_driver_config(config_path)
    remove_project_driver_builtin(builtin_name, config_path)
    click.echo(_("unregistered builtin: {builtin}").format(builtin=builtin_name))
    _echo_driver_config(config_path)


@driver.command(
    "show",
    help=_("Show effective NoneBot init kwargs generated from apeiria.drivers.toml."),
)
@click.option("--config", "config_arg", type=click.Path(dir_okay=False))
def driver_show(config_arg: str | None) -> None:
    kwargs = get_project_driver_kwargs(_config_path(config_arg))
    if not kwargs:
        click.echo("{}")
        return
    for key, value in kwargs.items():
        click.echo(f"{key}={value}")


def main() -> None:
    cli(prog_name="apeiria")


if __name__ == "__main__":
    main()
