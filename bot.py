import nonebot
from nonebot.adapters.console import Adapter as ConsoleAdapter
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)
driver.register_adapter(ConsoleAdapter)

# --- Core framework init ---
from apeiria.core.services.log import setup_logging

setup_logging()

# --- Load plugins (ORM, scheduler, etc.) ---
nonebot.load_builtin_plugins("echo")
nonebot.load_from_toml("pyproject.toml")

# --- Register ORM models & hooks (after plugins loaded) ---
import apeiria.core.hooks
import apeiria.core.models  # noqa: F401

if __name__ == "__main__":
    nonebot.run()
