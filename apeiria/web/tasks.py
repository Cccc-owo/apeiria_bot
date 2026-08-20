from __future__ import annotations

from typing import Any

from apeiria.jobs.package import PackageJob
from apeiria.jobs.runtime import get_job_runner


class TaskRunner:
    """Backwards-compatible facade over the new job execution system."""

    def __init__(self) -> None:
        self._runner = get_job_runner()

    async def start(  # noqa: PLR0913
        self,
        kind: str,
        name: str,
        pkg_requirement: str = "",
        *,
        module_name: str | None = None,
        uninstall: bool = False,
        keep_config: bool = False,
        update: bool = False,
    ) -> str:
        if update:
            operation = "update"
        elif uninstall:
            operation = "uninstall"
        else:
            operation = "install"
        job = PackageJob(
            kind,
            name,
            pkg_requirement,
            operation=operation,
            module_name=module_name,
            keep_config=keep_config,
        )
        return await self._runner.start(job)

    async def subscribe(self, task_id: str) -> Any | None:
        return await self._runner.subscribe(task_id)

    async def cancel(self, task_id: str) -> bool:
        return await self._runner.cancel(task_id)

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        return await self._runner.get_status(task_id)


_runner = TaskRunner()


def get_task_runner() -> TaskRunner:
    return _runner
