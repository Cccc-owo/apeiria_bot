from __future__ import annotations

import nonebot

from apeiria.infra.runtime.bootstrap import initialize_nonebot

initialize_nonebot()


def run() -> None:
    nonebot.run()


if __name__ == "__main__":
    run()
