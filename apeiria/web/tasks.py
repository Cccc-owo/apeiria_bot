"""Backwards-compatible task runner facade over the job execution system."""

from __future__ import annotations

from typing import Any

from apeiria.jobs.package import PackageJob
from apeiria.jobs.runtime import get_job_runner


class TaskRunner:
    """Backwards-compatible facade over the new job execution system."""

    def __init__(self) -> None:
        """Initialize the facade by resolving the underlying job runner."""
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
        """Start a package job and return its task id.

        Args:
            kind: Job kind, e.g. "plugin" or "adapter".
            name: Package name.
            pkg_requirement: Package requirement specifier, if any.
            module_name: Optional module name for adapters.
            uninstall: Whether the operation uninstalls the package.
            keep_config: Whether to keep configuration on uninstall.
            update: Whether the operation updates the package.

        Returns:
            The id of the started task.
        """
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
        """Subscribe to a task's event queue.

        Args:
            task_id: Id of the task to subscribe to.

        Returns:
            The task event queue, or None when the task is unknown.
        """
        return await self._runner.subscribe(task_id)

    async def cancel(self, task_id: str) -> bool:
        """Cancel a running task.

        Args:
            task_id: Id of the task to cancel.

        Returns:
            True when the task was cancelled; False otherwise.
        """
        return await self._runner.cancel(task_id)

    async def get_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the current status of a task.

        Args:
            task_id: Id of the task to inspect.

        Returns:
            The task status dictionary, or None when the task is unknown.
        """
        return await self._runner.get_status(task_id)


_runner = TaskRunner()


def get_task_runner() -> TaskRunner:
    """Return the global task runner instance."""
    return _runner
