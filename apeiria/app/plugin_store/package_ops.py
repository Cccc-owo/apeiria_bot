"""Plugin package operations shared by plugin-store workflows and CLI."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import Distribution, distributions
from pathlib import PurePosixPath

from apeiria.app.plugins.models import PluginUninstallResult
from apeiria.infra.config.plugins import plugin_config_service
from apeiria.infra.runtime.environment import (
    add_plugin_requirement,
    declared_plugin_requirements,
    discard_plugin_module_uninstall,
    discard_plugin_requirement_removal,
    plugin_site_packages_paths,
    remove_plugin_requirement,
    update_plugin_requirement,
)
from apeiria.package_ids import normalize_package_id
from apeiria.shared.plugin_introspection import invalidate_plugin_management_caches


@dataclass(frozen=True)
class PluginInstallResult:
    """Result of one plugin install or update operation."""

    requirement: str
    module_name: str


class StoreInstallError(RuntimeError):
    """Raised when a store-backed install operation fails."""


@dataclass(frozen=True)
class PluginUninstallRollbackPlan:
    """Rollback information for one plugin uninstall operation."""

    removed_requirement: bool
    restore_package_binding: bool


def _package_name_required_error() -> StoreInstallError:
    return StoreInstallError("package name is required")


def _plugin_module_name_required_error() -> StoreInstallError:
    return StoreInstallError("plugin module name is required")


def _automatic_module_resolution_error() -> StoreInstallError:
    return StoreInstallError(
        "could not determine plugin module automatically; use --module"
    )


def install_plugin_package(
    requirement: str,
    module_name: str,
    extra_args: tuple[str, ...] = (),
) -> PluginInstallResult:
    """Install a plugin package and bind its module into project config."""

    target = requirement.strip()
    resolved_module = module_name.strip()
    if not target:
        raise _package_name_required_error()
    if not resolved_module:
        raise _plugin_module_name_required_error()

    try:
        add_plugin_requirement(target, extra_args)
    except RuntimeError as exc:
        raise StoreInstallError(str(exc)) from exc

    try:
        plugin_config_service.bind_project_plugin_package(target, resolved_module)
    except Exception as exc:
        _rollback_plugin_install(target, extra_args, exc)
        raise AssertionError("unreachable") from exc
    discard_plugin_requirement_removal(target)
    discard_plugin_module_uninstall(resolved_module)
    invalidate_plugin_management_caches()

    return PluginInstallResult(
        requirement=target,
        module_name=resolved_module,
    )


def install_plugin_requirement_with_auto_module(
    requirement: str,
    extra_args: tuple[str, ...] = (),
) -> PluginInstallResult:
    """Install a plugin requirement and infer its module automatically."""

    target = requirement.strip()
    if not target:
        raise _package_name_required_error()

    declared_before = declared_plugin_requirements()
    distributions_before = _installed_distributions_by_name()
    try:
        add_plugin_requirement(target, extra_args)
    except RuntimeError as exc:
        raise StoreInstallError(str(exc)) from exc

    declared_requirement = _resolve_declared_requirement(target, declared_before)
    try:
        resolved_module = _infer_plugin_module(
            target,
            declared_requirement,
            distributions_before,
        )
        plugin_config_service.bind_project_plugin_package(
            declared_requirement,
            resolved_module,
        )
    except Exception as exc:
        _rollback_plugin_install(declared_requirement, extra_args, exc)
        raise AssertionError("unreachable") from exc
    discard_plugin_requirement_removal(declared_requirement)
    discard_plugin_module_uninstall(resolved_module)
    invalidate_plugin_management_caches()

    return PluginInstallResult(
        requirement=declared_requirement,
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
        raise _package_name_required_error()
    if not resolved_module:
        raise _plugin_module_name_required_error()

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
    invalidate_plugin_management_caches()

    return PluginUninstallResult(
        requirement=target,
        module_names=[resolved_module],
    )


def update_plugin_package(
    requirement: str,
    module_name: str,
    extra_args: tuple[str, ...] = (),
) -> PluginInstallResult:
    """Update one installed plugin package without changing its binding."""

    target = requirement.strip()
    resolved_module = module_name.strip()
    if not target:
        raise _package_name_required_error()
    if not resolved_module:
        raise _plugin_module_name_required_error()

    registered_modules = plugin_config_service.get_project_plugin_package_modules(
        target
    )
    if not registered_modules:
        msg = f"package {target} is not registered in project config"
        raise StoreInstallError(msg)
    if resolved_module not in registered_modules:
        msg = f"module {resolved_module} is not bound to package {target}"
        raise StoreInstallError(msg)

    try:
        update_plugin_requirement(target, extra_args)
    except RuntimeError as exc:
        raise StoreInstallError(str(exc)) from exc

    discard_plugin_requirement_removal(target)
    discard_plugin_module_uninstall(resolved_module)
    invalidate_plugin_management_caches()
    return PluginInstallResult(
        requirement=target,
        module_name=resolved_module,
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


def _resolve_declared_requirement(
    target: str,
    before: dict[str, str],
) -> str:
    current = declared_plugin_requirements()
    normalized_target = normalize_package_id(target)
    if normalized_target and normalized_target in current:
        return current[normalized_target]

    changed = {
        name: requirement
        for name, requirement in current.items()
        if before.get(name) != requirement
    }
    if len(changed) == 1:
        return next(iter(changed.values()))
    return target


def _installed_distributions_by_name() -> dict[str, Distribution]:
    paths = [str(path) for path in plugin_site_packages_paths()]
    installed: dict[str, Distribution] = {}
    if not paths:
        return installed
    for dist in distributions(path=paths):
        name = normalize_package_id(str(dist.metadata["Name"] or ""))
        if name:
            installed[name] = dist
    return installed


def _infer_plugin_module(
    raw_requirement: str,
    declared_requirement: str,
    distributions_before: dict[str, Distribution],
) -> str:
    candidates = _collect_plugin_candidates(
        raw_requirement,
        declared_requirement,
        distributions_before,
    )
    unique_values = sorted({value.strip() for value in candidates if value.strip()})
    if len(unique_values) == 1:
        return unique_values[0]
    raise _automatic_module_resolution_error()


def _collect_plugin_candidates(
    raw_requirement: str,
    declared_requirement: str,
    distributions_before: dict[str, Distribution],
) -> list[str]:
    candidates: list[str] = []
    for value in (declared_requirement, raw_requirement):
        candidates.extend(_plugin_candidates_from_requirement(value))
    for dist in _primary_distributions(
        declared_requirement,
        distributions_before,
    ):
        candidates.extend(_plugin_candidates_from_distribution(dist))
    return candidates


def _plugin_candidates_from_requirement(requirement: str) -> list[str]:
    target = requirement.strip()
    if not target:
        return []
    path_part = PurePosixPath(target.split("@", 1)[0].strip())
    candidate = path_part.name or path_part.parent.name
    candidate = candidate.replace("-", "_")
    return [candidate] if candidate else []


def _primary_distributions(
    declared_requirement: str,
    distributions_before: dict[str, Distribution],
) -> list[Distribution]:
    declared = normalize_package_id(declared_requirement)
    installed_now = _installed_distributions_by_name()
    if declared and declared in installed_now:
        return [installed_now[declared]]
    return [
        dist for name, dist in installed_now.items() if name not in distributions_before
    ]


def _plugin_candidates_from_distribution(dist: Distribution) -> list[str]:
    candidates: list[str] = []
    entry_points = list(getattr(dist, "entry_points", []) or [])
    for entry in entry_points:
        group = getattr(entry, "group", "")
        if group != "nonebot.plugin":
            continue
        value = getattr(entry, "value", "")
        module_name = str(value).split(":", 1)[0].strip()
        if module_name:
            candidates.append(module_name)
    if candidates:
        return candidates

    top_level = dist.read_text("top_level.txt") or ""
    for line in top_level.splitlines():
        module_name = line.strip()
        if module_name and not module_name.startswith("_"):
            candidates.append(module_name)
    return candidates
