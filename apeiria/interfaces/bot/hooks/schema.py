"""Schema hook — initialize or validate Apeiria database schema on startup."""

from nonebot import get_driver

from apeiria.infra.db.schema import ensure_database_ready


@get_driver().on_startup
async def ensure_schema() -> None:
    """Ensure the Apeiria database schema is ready before business hooks run."""
    await ensure_database_ready()
