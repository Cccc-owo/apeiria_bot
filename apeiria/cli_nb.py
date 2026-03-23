from __future__ import annotations

import asyncio
import sys
from typing import Literal

from packaging.requirements import Requirement

MODULE_TYPE = Literal["plugin", "adapter", "driver"]


class _ApeiriaConfigBridge:
    def add_dependency(self, *packages: Requirement, group: str | None = None) -> None:
        _ = packages, group

    def update_dependency(self, *packages: Requirement) -> None:
        _ = packages

    def remove_dependency(self, *packages: Requirement) -> list[Requirement]:
        return list(packages)


def _load_handlers() -> tuple[object, object, object, object, object]:
    try:
        from nb_cli.cli.utils import find_exact_package, format_package_results
        from nb_cli.handlers.adapter import list_adapters
        from nb_cli.handlers.driver import list_drivers
        from nb_cli.handlers.plugin import list_plugins
    except ModuleNotFoundError as exc:
        raise RuntimeError("nb-cli") from exc

    return (
        list_plugins,
        list_adapters,
        list_drivers,
        format_package_results,
        find_exact_package,
    )


def _load_environment_executor() -> object:
    try:
        from nb_cli.handlers.environment import EnvironmentExecutor
    except ModuleNotFoundError as exc:
        raise RuntimeError("nb-cli") from exc
    return EnvironmentExecutor


def search_store_packages(
    module_type: MODULE_TYPE,
    query: str | None = None,
) -> list[object]:
    list_plugins, list_adapters, list_drivers, _, _ = _load_handlers()
    if module_type == "plugin":
        return list(asyncio.run(list_plugins(query)))
    if module_type == "adapter":
        return list(asyncio.run(list_adapters(query)))
    return list(asyncio.run(list_drivers(query)))


def find_exact_store_package(
    module_type: MODULE_TYPE,
    value: str,
) -> object | None:
    needle = value.lower()
    for item in search_store_packages(module_type, value):
        if any(
            str(candidate).lower() == needle
            for candidate in (
                getattr(item, "name", ""),
                getattr(item, "module_name", ""),
                getattr(item, "project_link", ""),
            )
        ):
            return item
    return None


def format_store_packages(items: list[object]) -> str:
    _, _, _, format_package_results, _ = _load_handlers()
    return str(format_package_results(items))


def _run_environment_action(
    action: Literal["install", "update", "uninstall"],
    requirement: str,
    extra_args: tuple[str, ...] = (),
) -> None:
    environment_executor_cls = _load_environment_executor()

    async def _runner() -> None:
        executor = await environment_executor_cls.get(
            toml_manager=_ApeiriaConfigBridge(),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        package = Requirement(requirement)
        if action == "install":
            await executor.install(package, extra_args=extra_args)
        elif action == "update":
            await executor.update(package, extra_args=extra_args)
        else:
            await executor.uninstall(package, extra_args=extra_args)

    asyncio.run(_runner())


def install_package(requirement: str, extra_args: tuple[str, ...] = ()) -> None:
    _run_environment_action("install", requirement, extra_args)


def update_package(requirement: str, extra_args: tuple[str, ...] = ()) -> None:
    _run_environment_action("update", requirement, extra_args)


def uninstall_package(requirement: str, extra_args: tuple[str, ...] = ()) -> None:
    _run_environment_action("uninstall", requirement, extra_args)


def prompt_select_store_package(
    module_type: MODULE_TYPE,
    question: str,
    query: str | None = None,
) -> object:
    *_, find_exact_package = _load_handlers()
    items = search_store_packages(module_type, query)
    if not items:
        raise RuntimeError("empty-store")

    if query:
        needle = query.lower()
        for item in items:
            if any(
                str(candidate).strip().lower() == needle
                for candidate in (
                    getattr(item, "name", ""),
                    getattr(item, "module_name", ""),
                    getattr(item, "project_link", ""),
                )
            ):
                return item
        if len(items) == 1:
            return items[0]

    return asyncio.run(find_exact_package(question, None, items))


def prompt_select_text(question: str, items: list[str]) -> str:
    if not items:
        raise RuntimeError("empty-select")
    try:
        from nb_cli.cli.utils import CLI_DEFAULT_STYLE
        from noneprompt import Choice, ListPrompt
    except ModuleNotFoundError as exc:
        raise RuntimeError("nb-cli") from exc

    async def _runner() -> str:
        result = await ListPrompt(
            question,
            [Choice(item, item) for item in items],
        ).prompt_async(style=CLI_DEFAULT_STYLE)
        return str(result.data)

    return asyncio.run(_runner())
