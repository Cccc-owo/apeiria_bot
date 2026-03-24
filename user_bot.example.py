import nonebot


def configure(driver: object, nb: object = nonebot) -> None:
    """Project-local startup extension.

    Copy this file to ``user_bot.py`` and edit it freely.
    The repository ignores ``user_bot.py`` so local changes stay out of git.
    Runtime configuration from ``apeiria.config.toml`` is applied during
    ``nonebot.init(...)`` before this function runs.
    Legacy plugin config bridges are auto-registered from framework and
    enabled plugins before ``nonebot.init(...)`` runs.
    ``pyproject.toml`` is loaded afterwards for compatibility with native
    NoneBot plugin declarations.
    Plugin declarations from ``apeiria.plugins.toml`` are loaded separately.
    Adapter declarations from ``apeiria.adapters.toml`` are registered after
    this function runs.
    Driver declarations from ``apeiria.drivers.toml`` are applied during
    ``nonebot.init(...)`` before this function runs.
    """

    _ = (driver, nb)

    # 1. Attach project-local lifecycle hooks.
    #
    # @driver.on_startup
    # async def _startup() -> None:
    #     nb.logger.info("custom startup hook ready")
    #
    # @driver.on_shutdown
    # async def _shutdown() -> None:
    #     nb.logger.info("custom shutdown hook finished")

    # 2. Register adapters manually if you want to override the default order.
    #
    # from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
    # driver.register_adapter(OneBotV11Adapter)
    #
    # 3. Put any project-local initialization here.
    #
    # from pathlib import Path
    # data_dir = Path("data") / "custom"
    # data_dir.mkdir(parents=True, exist_ok=True)

    # Keep this function empty until you need local customization.
