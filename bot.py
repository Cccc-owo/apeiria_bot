"""Apeiria Bot entry point.

Delegates to :func:`apeiria.cli.main.main`, which dispatches to the core
subcommands (``init``, ``run``, ``reset_password``).

"""

from apeiria.cli.main import main

if __name__ == "__main__":
    main()
