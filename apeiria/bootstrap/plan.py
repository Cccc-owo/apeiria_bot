"""DAG-based startup orchestration for bootstrap steps."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Any

from nonebot.log import logger

StepFn = Callable[..., Any]


class BootstrapPlan:
    """Orchestrate named startup steps and run them in dependency order.

    Each step is registered under a name together with optional dependencies
    on other step names. :meth:`run` executes the steps in topological order
    and collects the names of the steps that succeeded and failed.
    """

    def __init__(self) -> None:
        """Initialize an empty bootstrap plan."""
        self._steps: dict[str, StepFn] = {}
        self._depends: dict[str, list[str]] = {}

    def add_step(self, name: str, fn: StepFn, depends: list[str] | None = None) -> None:
        """Register a bootstrap step together with its dependencies.

        Args:
            name: Unique name identifying this step.
            fn: Callable invoked when this step runs.
            depends: Names of steps that must complete before this one runs.
        """
        self._steps[name] = fn
        self._depends[name] = list(depends or [])

    def run(self, plan_name: str) -> BootstrapResult:
        """Run all registered steps in topological order.

        Args:
            plan_name: Name of the plan, used only for logging.

        Returns:
            A :class:`BootstrapResult` holding the names of steps that
            succeeded and failed.
        """
        logger.info("Running bootstrap plan: {}", plan_name)
        order = _topo_sort(self._steps, self._depends)

        success: list[str] = []
        failed: list[str] = []

        for name in order:
            fn = self._steps[name]
            logger.debug("Bootstrap step: {}", name)
            try:
                fn()
                success.append(name)
            except Exception:  # noqa: BLE001
                logger.opt(exception=True).error("Bootstrap step failed: {}", name)
                failed.append(name)
                logger.error("Bootstrap stopped after failed step: {}", name)
                break

        logger.success(
            "Bootstrap complete: {} succeeded, {} failed",
            len(success),
            len(failed),
        )
        return BootstrapResult(success=tuple(success), failed=tuple(failed))


class BootstrapResult:
    """Container holding the outcome of a bootstrap run.

    Stores the names of the steps that succeeded and the steps that failed,
    so callers can inspect how the plan completed.
    """

    __slots__ = ("failed", "success")

    def __init__(self, success: tuple[str, ...], failed: tuple[str, ...]) -> None:
        """Initialize a bootstrap result.

        Args:
            success: Names of the steps that completed successfully.
            failed: Names of the steps that raised during execution.
        """
        self.success = success
        self.failed = failed

    @property
    def ok(self) -> bool:
        """Return whether no steps failed."""
        return len(self.failed) == 0


def _topo_sort(
    steps: dict[str, StepFn],
    depends: dict[str, list[str]],
) -> list[str]:
    """Return the step names ordered so dependencies run before dependents.

    Args:
        steps: Mapping of step name to its callable.
        depends: Mapping of step name to the names it directly depends on.

    Returns:
        A topological ordering of the step names. Steps involved in a cycle or
        with missing dependencies are omitted.
    """
    in_degree: dict[str, int] = dict.fromkeys(steps, 0)

    for name, deps in depends.items():
        for _dep in deps:
            in_degree[name] += 1

    queue = deque(name for name, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for other_name, other_deps in depends.items():
            if node in other_deps:
                in_degree[other_name] -= 1
                if in_degree[other_name] == 0:
                    queue.append(other_name)

    if len(result) != len(steps):
        missing = set(steps) - set(result)
        logger.warning("Bootstrap cycle or missing deps: {}", missing)

    return result
