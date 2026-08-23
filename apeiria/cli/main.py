"""Define the root Click command group for the Apeiria Bot CLI."""

from __future__ import annotations

import click

from apeiria.cli.init_cmd import init_cmd
from apeiria.cli.reset_password_cmd import reset_password_cmd
from apeiria.cli.run_cmd import run_cmd


@click.group()
@click.option(
    "-c",
    "--cwd",
    default=None,
    help="Project root directory",
)
@click.pass_context
def cli(_ctx: click.Context, cwd: str | None) -> None:
    """Run the Apeiria Bot CLI.

    Args:
        _ctx (click.Context): The Click command context (unused).
        cwd (str | None): Project root directory to change into, if provided.
    """
    if cwd is not None:
        import os
        from pathlib import Path

        os.chdir(Path(cwd).resolve())


cli.add_command(init_cmd)
cli.add_command(run_cmd)
cli.add_command(reset_password_cmd)


def main() -> None:
    """Run the Apeiria Bot CLI."""
    cli()
