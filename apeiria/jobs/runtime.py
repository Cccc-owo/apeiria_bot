"""Provide the singleton job runner used across the application."""

from __future__ import annotations

from apeiria.jobs.base import JobRunner

_runner = JobRunner()


def get_job_runner() -> JobRunner:
    """Return the shared job runner instance.

    Returns:
        The singleton :class:`JobRunner` used by the application.
    """
    return _runner
