"""Scheduler service — wraps APScheduler with registration API."""

from __future__ import annotations

from typing import Any

from nonebot.log import logger
from nonebot_plugin_apscheduler import scheduler as _scheduler


class SchedulerService:
    """Wraps APScheduler, provides unified registration and job inspection."""

    @property
    def raw(self):  # noqa: ANN201
        """Access the underlying APScheduler instance."""
        return _scheduler

    def scheduled_job(
        self,
        trigger: str,
        **kwargs: Any,
    ) -> Any:
        """Decorator to register a scheduled job.

        Usage:
            @scheduler_service.scheduled_job("cron", hour=0, minute=0)
            async def daily_reset():
                ...
        """
        return _scheduler.scheduled_job(trigger, **kwargs)

    def add_job(self, func: Any, trigger: str, **kwargs: Any) -> str:
        """Add a job programmatically. Returns job ID."""
        job = _scheduler.add_job(func, trigger, **kwargs)
        logger.debug("Scheduled job added: {} ({})", job.id, trigger)
        return str(job.id)

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job by ID."""
        _scheduler.remove_job(job_id)
        logger.debug("Scheduled job removed: {}", job_id)

    def get_jobs(self) -> list[dict[str, Any]]:
        """List all registered jobs (for Web UI)."""
        jobs = _scheduler.get_jobs()
        return [
            {
                "id": str(job.id),
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
            }
            for job in jobs
        ]

    def get_job(self, job_id: str) -> Any | None:
        """Return one job by ID if it exists."""
        return _scheduler.get_job(job_id)

    def pause_job(self, job_id: str) -> None:
        _scheduler.pause_job(job_id)

    def resume_job(self, job_id: str) -> None:
        _scheduler.resume_job(job_id)


scheduler_service = SchedulerService()
