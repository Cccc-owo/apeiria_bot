from __future__ import annotations

from apeiria.jobs.base import JobRunner

_runner = JobRunner()


def get_job_runner() -> JobRunner:
    return _runner
