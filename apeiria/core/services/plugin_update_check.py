"""Check external plugin package updates against PyPI."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from apeiria.domains.plugins.service import PluginCatalogItem


_HTTP_NOT_FOUND = 404


@dataclass(frozen=True)
class PluginUpdateCheckResult:
    """One plugin update check result."""

    module_name: str
    package_name: str
    current_version: str | None
    latest_version: str | None
    has_update: bool
    checked: bool
    error: str | None = None


@dataclass
class _CachedResult:
    result: PluginUpdateCheckResult
    expires_at: datetime


class PluginUpdateCheckService:
    """Check current plugin package versions against PyPI JSON metadata."""

    _CACHE_TTL = timedelta(minutes=10)
    _TIMEOUT_SECONDS = 5.0
    _USER_AGENT = "apeiria-bot-plugin-update-check/1.0"

    def __init__(self) -> None:
        self._cache: dict[str, _CachedResult] = {}

    async def check_plugins(
        self,
        plugins: list[PluginCatalogItem],
        *,
        force_refresh: bool = False,
    ) -> list[PluginUpdateCheckResult]:
        candidates = [
            plugin
            for plugin in plugins
            if plugin.can_uninstall and plugin.installed_package
        ]
        results = await asyncio.gather(
            *[
                self.check_plugin(
                    plugin.module_name,
                    plugin.installed_package or "",
                    force_refresh=force_refresh,
                )
                for plugin in candidates
            ]
        )
        return list(results)

    async def check_plugin(
        self,
        module_name: str,
        package_name: str,
        *,
        force_refresh: bool = False,
    ) -> PluginUpdateCheckResult:
        requirement = package_name.strip()
        parsed_name = _parse_package_name(requirement)
        if not parsed_name:
            return PluginUpdateCheckResult(
                module_name=module_name,
                package_name=requirement,
                current_version=None,
                latest_version=None,
                has_update=False,
                checked=False,
                error="package version check is not supported for this source",
            )

        cache_key = canonicalize_name(parsed_name)
        now = datetime.now(UTC)
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached and cached.expires_at > now:
                return PluginUpdateCheckResult(
                    **{
                        **cached.result.__dict__,
                        "module_name": module_name,
                        "package_name": requirement,
                    }
                )

        current_version = _read_installed_package_version(parsed_name)
        if not current_version:
            result = PluginUpdateCheckResult(
                module_name=module_name,
                package_name=requirement,
                current_version=None,
                latest_version=None,
                has_update=False,
                checked=False,
                error="installed package version is unavailable",
            )
            self._cache[cache_key] = _CachedResult(
                result=result,
                expires_at=now + self._CACHE_TTL,
            )
            return result

        try:
            latest_version = await asyncio.to_thread(
                self._fetch_latest_version,
                parsed_name,
            )
        except RuntimeError as exc:
            result = PluginUpdateCheckResult(
                module_name=module_name,
                package_name=requirement,
                current_version=current_version,
                latest_version=None,
                has_update=False,
                checked=False,
                error=str(exc),
            )
            self._cache[cache_key] = _CachedResult(
                result=result,
                expires_at=now + self._CACHE_TTL,
            )
            return result

        result = PluginUpdateCheckResult(
            module_name=module_name,
            package_name=requirement,
            current_version=current_version,
            latest_version=latest_version,
            has_update=_has_newer_version(current_version, latest_version),
            checked=True,
            error=None,
        )
        self._cache[cache_key] = _CachedResult(
            result=result,
            expires_at=now + self._CACHE_TTL,
        )
        return result

    def _fetch_latest_version(self, package_name: str) -> str:
        request = Request(
            f"https://pypi.org/pypi/{package_name}/json",
            headers={"User-Agent": self._USER_AGENT},
        )
        try:
            with urlopen(request, timeout=self._TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == _HTTP_NOT_FOUND:
                msg = "package is not published on PyPI"
                raise RuntimeError(msg) from exc
            msg = f"package check failed: HTTP {exc.code}"
            raise RuntimeError(msg) from exc
        except (OSError, TimeoutError, URLError, ValueError) as exc:
            msg = "failed to query PyPI"
            raise RuntimeError(msg) from exc

        info = payload.get("info")
        version = info.get("version") if isinstance(info, dict) else None
        if not isinstance(version, str) or not version.strip():
            msg = "latest version is unavailable"
            raise RuntimeError(msg)
        return version.strip()


def _parse_package_name(requirement: str) -> str | None:
    target = requirement.strip()
    if not target:
        return None
    try:
        return Requirement(target).name
    except InvalidRequirement:
        return None


def _read_installed_package_version(package_name: str) -> str | None:
    try:
        return package_version(package_name)
    except PackageNotFoundError:
        return None


def _has_newer_version(current_version: str, latest_version: str) -> bool:
    try:
        return Version(latest_version) > Version(current_version)
    except InvalidVersion:
        return latest_version.strip() != current_version.strip()


plugin_update_check_service = PluginUpdateCheckService()
