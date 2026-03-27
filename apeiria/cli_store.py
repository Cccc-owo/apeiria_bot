"""Reusable store install operations shared by CLI and Web UI."""

from __future__ import annotations

from dataclasses import dataclass

from apeiria.config.plugins import plugin_config_service
from apeiria.runtime_env import add_plugin_requirement, remove_plugin_requirement


@dataclass(frozen=True)
class PluginInstallResult:
    """Result of one plugin install operation."""

    requirement: str
    module_name: str


@dataclass(frozen=True)
class PluginUninstallResult:
    """Result of one plugin uninstall operation."""

    requirement: str
    module_names: list[str]


class StoreInstallError(RuntimeError):
    """Raised when a store-backed install operation fails."""


@dataclass(frozen=True)
class PluginUninstallRollbackPlan:
    """Rollback information for one plugin uninstall operation."""

    removed_requirement: bool
    restore_package_binding: bool


def _missing_package_name_error() -> StoreInstallError:
    return StoreInstallError("package name is required")


def _missing_plugin_module_name_error() -> StoreInstallError:
    return StoreInstallError("plugin module name is required")


def install_plugin_package(
    requirement: str,
    module_name: str,
    extra_args: tuple[str, ...] = (),
) -> PluginInstallResult:
    """Install a plugin package and bind its module into project config."""

    target = requirement.strip()
    resolved_module = module_name.strip()
    if not target:
        raise _missing_package_name_error()
    if not resolved_module:
        raise _missing_plugin_module_name_error()

    try:
        add_plugin_requirement(target, extra_args)
    except RuntimeError as exc:
        raise StoreInstallError(str(exc)) from exc

    try:
        plugin_config_service.bind_project_plugin_package(target, resolved_module)
    except Exception as exc:
        _rollback_plugin_install(target, extra_args, exc)
        raise AssertionError("unreachable") from exc

    return PluginInstallResult(
        requirement=target,
        module_name=resolved_module,
    )


def uninstall_plugin_package(
    requirement: str,
    module_name: str,
    extra_args: tuple[str, ...] = (),
) -> PluginUninstallResult:
    """Uninstall or unbind one plugin module from a package."""

    target = requirement.strip()
    resolved_module = module_name.strip()
    if not target:
        raise _missing_package_name_error()
    if not resolved_module:
        raise _missing_plugin_module_name_error()

    registered_modules = plugin_config_service.get_project_plugin_package_modules(
        target
    )
    package_was_bound = bool(registered_modules)
    if package_was_bound and resolved_module not in registered_modules:
        msg = f"module {resolved_module} is not bound to package {target}"
        raise StoreInstallError(msg)

    removed_requirement = not package_was_bound or len(registered_modules) == 1

    if removed_requirement:
        try:
            remove_plugin_requirement(target, extra_args)
        except RuntimeError as exc:
            raise StoreInstallError(str(exc)) from exc

    try:
        plugin_config_service.remove_project_plugin_module(resolved_module)
    except Exception as exc:
        _rollback_plugin_uninstall(
            target,
            resolved_module,
            extra_args,
            exc,
            PluginUninstallRollbackPlan(
                removed_requirement=removed_requirement,
                restore_package_binding=package_was_bound,
            ),
        )
        raise AssertionError("unreachable") from exc

    return PluginUninstallResult(
        requirement=target,
        module_names=[resolved_module],
    )


def _rollback_plugin_install(
    target: str,
    extra_args: tuple[str, ...],
    exc: Exception,
) -> None:
    try:
        remove_plugin_requirement(target, extra_args)
    except RuntimeError as rollback_exc:
        msg = (
            f"{exc}\n"
            "rollback failed: "
            f"{target} is still installed in the extension environment\n"
            f"{rollback_exc}"
        )
        raise StoreInstallError(msg) from rollback_exc
    raise StoreInstallError(str(exc)) from exc


def _rollback_plugin_uninstall(
    target: str,
    module_name: str,
    extra_args: tuple[str, ...],
    exc: Exception,
    plan: PluginUninstallRollbackPlan,
) -> None:
    try:
        if plan.removed_requirement:
            add_plugin_requirement(target, extra_args)
        if plan.restore_package_binding:
            plugin_config_service.bind_project_plugin_package(target, module_name)
        else:
            plugin_config_service.add_project_plugin_module(module_name)
    except Exception as rollback_exc:
        msg = (
            f"{exc}\n"
            "rollback failed: "
            f"{target} could not be restored to its previous state\n"
            f"{rollback_exc}"
        )
        raise StoreInstallError(msg) from rollback_exc
    raise StoreInstallError(str(exc)) from exc
