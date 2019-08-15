import asyncio
import importlib
import logging
from functools import wraps
from . import tools


def extra_setup(func):
    @wraps(func)
    def _new_setup(bot):
        try:
            module = importlib.reload(tools)
            cog = module.ToolBox(bot)
            bot.remove_cog("Sinbad's Toolbox")
            bot.add_cog(cog)
        finally:  # Yes, I am intentionally returning in a finally statement.
            return func(bot)

    return _new_setup
