from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_REQUIREMENT_NAME = re.compile(r"^[A-Za-z0-9._-]+")

_MIN_RECORD_PARTS = 2

BUILTIN_LIST = [
    "admin",
    "help",
    "repeater",
    "trigger_reply",
    "friendship",
    "relay",
    "self_revoke",
]


@dataclass
class PluginManifest:
    name: str
    path_or_module: str
    enabled: bool
    source: str  # "builtin" | "local" | "pypi" | "dependency"
    config_module: str | None = None


def requirement_to_module(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement.strip())
    base = match.group(0) if match else requirement
    base = base.split("[", 1)[0]
    return base.replace("-", "_")


def _requirement_base_name(requirement: str) -> str:
    match = _REQUIREMENT_NAME.match(requirement.strip())
    base = match.group(0) if match else requirement
    return base.split("[", 1)[0]


def _normalize_dist_name(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")


def _default_venv_site_packages() -> Path | None:
    venv_path = Path(".apeiria/.venv")
    for lib_dir in sorted(venv_path.glob("lib/python*/site-packages")):
        return lib_dir
    return None


def _top_module_from_record(record_text: str | None, dist_name: str) -> str | None:
    if not record_text:
        return None
    normalized = _normalize_dist_name(dist_name)
    fallback: str | None = None
    for line in record_text.splitlines():
        entry = line.split(",", 1)[0].strip()
        if not entry:
            continue
        parts = entry.split("/")
        if len(parts) < _MIN_RECORD_PARTS:
            continue
        top = parts[0]
        if top.endswith((".dist-info", ".data")):
            continue
        if parts[1] != "__init__.py":
            continue
        if _normalize_dist_name(top) != normalized:
            return top
        if fallback is None:
            fallback = top
    return fallback


def _top_module_from_distinfo(dist_name: str, site_packages: Path) -> str | None:
    import importlib.metadata as md

    normalized = _normalize_dist_name(dist_name)
    try:
        for dist in md.distributions(path=[str(site_packages)]):
            meta_name = dist.metadata["Name"] if dist.metadata else None
            if meta_name is None or _normalize_dist_name(meta_name) != normalized:
                continue
            top_level = dist.read_text("top_level.txt")
            if top_level:
                for line in top_level.splitlines():
                    stripped = line.strip()
                    if stripped:
                        return stripped
            return _top_module_from_record(dist.read_text("RECORD"), dist_name)
    except (md.PackageNotFoundError, OSError):
        return None
    return None


def resolve_pypi_module(
    requirement: str,
    config_module: str | None = None,
    venv_site_packages: Path | None = None,
) -> str:
    if config_module:
        return config_module
    site_packages = venv_site_packages or _default_venv_site_packages()
    if site_packages is not None:
        dist_name = _requirement_base_name(requirement)
        resolved = _top_module_from_distinfo(dist_name, site_packages)
        if resolved:
            return resolved
    return requirement_to_module(requirement)


def read_installed_version(requirement: str) -> str | None:
    import importlib.metadata as md

    dist_name = _requirement_base_name(requirement)
    site_packages = _default_venv_site_packages()
    if site_packages is None:
        return None
    normalized = _normalize_dist_name(dist_name)
    try:
        for dist in md.distributions(path=[str(site_packages)]):
            meta_name = dist.metadata["Name"] if dist.metadata else None
            if meta_name is None:
                continue
            if _normalize_dist_name(meta_name) == normalized:
                return dist.version
    except (md.PackageNotFoundError, OSError):
        return None
    return None


def framework_version() -> str | None:
    """The Apeiria framework version, used for built-in plugins that ship with it."""
    import tomllib

    p = Path("pyproject.toml")
    if not p.is_file():
        return None
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        return data.get("project", {}).get("version")
    except (OSError, tomllib.TOMLDecodeError):
        return None


def read_local_plugin_version(plugin_path: Path) -> str | None:
    """Best-effort version for a local (folder) plugin."""
    pyproject = plugin_path / "pyproject.toml"
    if pyproject.is_file():
        import tomllib

        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            return data.get("project", {}).get("version")
        except (OSError, tomllib.TOMLDecodeError):
            pass
    init = plugin_path / "__init__.py"
    if init.is_file():
        try:
            text = init.read_text(encoding="utf-8")
        except OSError:
            return None
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", text)
        if match:
            return match.group(1)
    return None


def resolve_version(
    *,
    meta: dict | None,
    source: str,
    requirement: str | None = None,
    module: str | None = None,
    path: str | None = None,
) -> str | None:
    """Resolve a plugin's version by NoneBot spec precedence.

    1. ``PluginMetadata.extra["version"]`` (the plugin author's declared version).
    2. The installed distribution version (PyPI / dependency plugins).
    3. The framework version for built-in plugins.
    4. A local plugin's own declared version, if any.
    """
    declared = (meta or {}).get("version")
    if declared:
        return str(declared)

    if source in ("pypi", "dependency"):
        for candidate in (requirement, module):
            if candidate:
                result = read_installed_version(candidate)
                if result:
                    return result
        return None

    if source == "builtin":
        return framework_version()

    if source == "local":
        return read_local_plugin_version(Path(path)) if path else None

    return None


def local_plugin_module_name(plugin_dir: Path) -> str | None:
    """Return a valid import module name for a local plugin directory.

    The plugin directory's parent name is used as the top-level package, so
    ``.apeiria/plugins/foo`` becomes ``plugins.foo``. Returns ``None`` when
    either segment is not a valid Python identifier.
    """
    parent = plugin_dir.parent.name
    name = plugin_dir.name
    if not parent.isidentifier() or not name.isidentifier():
        return None
    return f"{parent}.{name}"


def manifest_module_candidate(manifest: PluginManifest) -> str:
    if manifest.source == "pypi":
        return resolve_pypi_module(manifest.path_or_module, manifest.config_module)
    if manifest.source == "local":
        path = Path(manifest.path_or_module)
        return local_plugin_module_name(path) or path.name
    return manifest.path_or_module.rsplit(".", 1)[-1]


def _load_plugins_yaml() -> dict:
    yaml_path = Path(".apeiria/plugins.yaml")
    if not yaml_path.exists():
        return {"dirs": [], "packages": {}, "states": {}}
    return yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}


def _is_enabled(name: str, data: dict) -> bool:
    states = data.get("states") or {}
    if name in states:
        return bool(states[name].get("enabled", True))
    return True


def scan_plugins() -> list[PluginManifest]:
    data = _load_plugins_yaml()
    dirs = data.get("dirs") or []
    packages = data.get("packages") or {}

    result: list[PluginManifest] = [
        PluginManifest(
            name=name,
            path_or_module=f"apeiria.builtin_plugins.{name}",
            enabled=_is_enabled(name, data),
            source="builtin",
        )
        for name in BUILTIN_LIST
    ]

    for scan_dir in dirs:
        dir_path = Path(scan_dir)
        if not dir_path.is_dir():
            continue
        for entry in sorted(dir_path.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            init_file = entry / "__init__.py"
            if not init_file.is_file():
                continue
            name = entry.name
            result.append(
                PluginManifest(
                    name=name,
                    path_or_module=str(entry.resolve()),
                    enabled=_is_enabled(name, data),
                    source="local",
                )
            )

    for pkg_name, pkg_info in packages.items():
        if isinstance(pkg_info, str):
            requirement = pkg_info
            config_module = None
        else:
            requirement = (
                pkg_info.get("package") or pkg_info.get("requirement") or pkg_name
            )
            config_module = pkg_info.get("module") or None
        result.append(
            PluginManifest(
                name=pkg_name,
                path_or_module=requirement,
                enabled=_is_enabled(pkg_name, data),
                source="pypi",
                config_module=config_module,
            )
        )

    return result
