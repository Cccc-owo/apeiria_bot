"""Define long-running background job primitives and their lifecycle runner."""

from __future__ import annotations

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterable
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from nonebot.log import logger

if TYPE_CHECKING:
    from apeiria.jobs.subprocess import SubprocessExecutor

_JOB_CLEANUP_DELAY = 3600.0
_HISTORY_LIMIT = 1000


class JobStatus(StrEnum):
    """Enumeration of the possible lifecycle states of a job."""

    PENDING = "pending"
    RUNNING = "running"
    CANCELLING = "cancelling"
    DONE = "done"
    ERROR = "error"
    CANCELLED = "cancelled"


class JobError(RuntimeError):
    """Raised when a job reaches a known failure state."""


class Job(ABC):
    """Base class for long-running background jobs."""

    def __init__(self, *, kind: str, lock_name: str | None = None) -> None:
        """Initialize a job.

        Args:
            kind: Label for the kind of work this job performs.
            lock_name: Optional name of the lock that serializes this job.
        """
        self.id = uuid.uuid4().hex
        self.kind = kind
        self.lock_name = lock_name
        self.status = JobStatus.PENDING
        self.cancel_event = asyncio.Event()
        self.error_message: str | None = None
        self.created_at = time.monotonic()
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.rollback_needed = False
        self._history: deque[dict[str, Any]] = deque(maxlen=_HISTORY_LIMIT)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._executor: SubprocessExecutor | None = None

    @abstractmethod
    async def run(self) -> None:
        """Execute the job.

        Raise JobError for expected failures. The runner owns rollback and
        terminal status transitions.
        """

    def snapshot(self) -> None:  # noqa: B027
        """Capture a rollback snapshot before mutating shared resources."""

    async def rollback(self) -> None:  # noqa: B027
        """Roll back side effects when the job fails or is cancelled."""

    def attach_executor(self, executor: SubprocessExecutor) -> None:
        """Attach a subprocess executor so cancellation can terminate the process.

        Args:
            executor: The executor managing the job's active subprocess.
        """
        self._executor = executor

    def detach_executor(self) -> None:
        """Clear the previously attached subprocess executor."""
        self._executor = None

    async def cancel(self) -> None:
        """Request cancellation of the job and terminate its subprocess."""
        self.cancel_event.set()
        if self._executor is not None:
            self._executor.terminate()

    def emit(self, event: dict[str, Any]) -> None:
        """Record an event in job history and broadcast it to subscribers.

        Args:
            event: The event payload to publish; the task id is added if absent.
        """
        event.setdefault("task_id", self.id)
        self._history.append(event)
        for queue in list(self._subscribers):
            queue.put_nowait(event)

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Return a queue that replays history and receives future events.

        Returns:
            A new asyncio queue populated with prior events that will also
            receive every later event emitted by this job.
        """
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        for event in self._history:
            queue.put_nowait(event)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a previously returned subscriber queue.

        Args:
            queue: The subscriber queue to detach.
        """
        self._subscribers.discard(queue)

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable snapshot of the job's status fields.

        Returns:
            A dictionary of job id, kind, status and timing information.
        """
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status.value,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


class JobRunner:
    """Registry and lifecycle owner for :class:`Job` instances."""

    def __init__(self) -> None:
        """Initialize the runner with empty registries and per-kind locks."""
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._git_lock = asyncio.Lock()
        self._apeiria_lock = asyncio.Lock()

    @property
    def jobs(self) -> dict[str, Job]:
        """Return the registry of tracked jobs keyed by job id."""
        return self._jobs

    async def start(self, job: Job) -> str:
        """Register and start a job, returning its id.

        Args:
            job: The job to run; a job already registered returns its id.

        Returns:
            The id of the started job.
        """
        if job.id in self._jobs:
            return job.id
        self._jobs[job.id] = job
        task = asyncio.create_task(self._run(job))
        self._tasks[job.id] = task

        def _on_done(done_task: asyncio.Task[Any]) -> None:
            """Finalize the job when its task completes, scheduling cleanup.

            Args:
                done_task: The completed asyncio task for the job.
            """
            self._tasks.pop(job.id, None)
            job.finished_at = time.monotonic()
            if job.status in (JobStatus.DONE, JobStatus.ERROR, JobStatus.CANCELLED):
                done_task.get_loop().call_later(
                    _JOB_CLEANUP_DELAY,
                    self._jobs.pop,
                    job.id,
                    None,
                )
            else:
                job.status = JobStatus.CANCELLED
                job.emit({"type": "cancelled", "message": "任务已取消"})
                done_task.get_loop().call_later(
                    _JOB_CLEANUP_DELAY,
                    self._jobs.pop,
                    job.id,
                    None,
                )
                logger.warning(
                    "Job {} ended in unexpected status, marked cancelled", job.id
                )

        task.add_done_callback(_on_done)
        return job.id

    async def _run(self, job: Job) -> None:
        """Run a job under its serialization lock, handling terminal failures.

        Args:
            job: The job to execute.
        """
        job.status = JobStatus.RUNNING
        job.started_at = time.monotonic()
        lock = self._lock_for(job)
        try:
            if lock is not None:
                async with lock:
                    await self._run_with_rollback(job)
            else:
                await self._run_with_rollback(job)
        except asyncio.CancelledError:
            if job.status not in (JobStatus.CANCELLING, JobStatus.CANCELLED):
                job.status = JobStatus.CANCELLED
                job.emit({"type": "cancelled", "message": "任务已取消"})
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job {} failed unexpectedly", job.id)
            job.error_message = str(exc)
            job.emit({"type": "error", "ok": False, "message": str(exc)})
            if job.rollback_needed:
                try:
                    await job.rollback()
                except Exception as rb_exc:  # noqa: BLE001
                    logger.exception("Rollback failed for job {}", job.id)
                    job.error_message = f"{exc}；回滚失败: {rb_exc}"
                    job.emit(
                        {
                            "type": "error",
                            "ok": False,
                            "message": job.error_message,
                        }
                    )
            job.status = JobStatus.ERROR

    async def _run_with_rollback(self, job: Job) -> None:
        """Run a job and roll back its side effects on failure or cancellation.

        Args:
            job: The job to execute.
        """
        try:
            job.snapshot()
            await job.run()
            if job.status is not JobStatus.CANCELLED:
                job.emit({"type": "done", "ok": True, "message": f"{job.kind} 完成"})
                job.status = JobStatus.DONE
        except asyncio.CancelledError:
            job.status = JobStatus.CANCELLING
            job.emit({"type": "cancelled", "message": "任务已取消，正在回滚"})
            if job.rollback_needed:
                try:
                    await job.rollback()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Rollback failed for job {}", job.id)
                    job.error_message = f"回滚失败: {exc}"
                    job.emit(
                        {"type": "error", "ok": False, "message": job.error_message}
                    )
            job.status = JobStatus.CANCELLED
            raise
        except JobError as exc:
            job.error_message = str(exc)
            job.emit({"type": "error", "ok": False, "message": str(exc)})
            if job.rollback_needed:
                try:
                    await job.rollback()
                except Exception as rb_exc:  # noqa: BLE001
                    logger.exception("Rollback failed for job {}", job.id)
                    job.error_message = f"{exc}；回滚失败: {rb_exc}"
                    job.emit(
                        {
                            "type": "error",
                            "ok": False,
                            "message": job.error_message,
                        }
                    )
            job.status = JobStatus.ERROR

    def _lock_for(self, job: Job) -> asyncio.Lock | None:
        """Return the asyncio lock that serializes a job, if any.

        Args:
            job: The job whose lock is needed.

        Returns:
            The matching lock, or None when the job requires no lock.
        """
        if job.lock_name == "git":
            return self._git_lock
        if job.lock_name == "apeiria":
            return self._apeiria_lock
        return None

    async def subscribe(self, job_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        """Return a subscriber queue for a job id, or None if the job is unknown.

        Args:
            job_id: The id of the job to subscribe to.

        Returns:
            A subscriber queue for the job, or None when the job is not found.
        """
        job = self._jobs.get(job_id)
        return job.subscribe() if job is not None else None

    async def cancel(self, job_id: str) -> bool:
        """Request cancellation of a running job.

        Args:
            job_id: The id of the job to cancel.

        Returns:
            True when cancellation was initiated, False otherwise.
        """
        job = self._jobs.get(job_id)
        if job is None or job.status in (
            JobStatus.DONE,
            JobStatus.ERROR,
            JobStatus.CANCELLED,
            JobStatus.CANCELLING,
        ):
            return False
        await job.cancel()
        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
        return True

    async def get_status(self, job_id: str) -> dict[str, Any] | None:
        """Return a status snapshot for a job id, or None if the job is unknown.

        Args:
            job_id: The id of the job to inspect.

        Returns:
            The job status dictionary, or None when the job is not found.
        """
        job = self._jobs.get(job_id)
        return job.to_dict() if job is not None else None


def drain_queue(queue: asyncio.Queue[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    """Yield leftover events currently buffered on a subscriber queue.

    Args:
        queue: The subscriber queue to drain.

    Yields:
        Each pending event in the queue, drained in order.
    """
    while not queue.empty():
        yield queue.get_nowait()
