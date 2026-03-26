from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import logging
    from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        tomllib = None


def atomic_write_text(target: Path, text: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_file = target.with_suffix(f"{target.suffix}.tmp")
    temp_file.write_text(text, encoding="utf-8")
    temp_file.replace(target)


def load_toml_dict(
    config_path: Path,
    *,
    logger: logging.Logger,
    missing_dependency_message: str,
) -> dict[str, Any]:
    if tomllib is None:
        logger.warning(missing_dependency_message)
        return {}
    if not config_path.is_file():
        return {}

    try:
        with config_path.open("rb") as file:
            data = tomllib.load(file)
    except OSError as exc:
        logger.warning("Skip loading %s: %s", config_path.name, exc)
        return {}
    except tomllib.TOMLDecodeError as exc:
        logger.warning("Skip loading %s: invalid TOML (%s)", config_path.name, exc)
        return {}

    return data if isinstance(data, dict) else {}
