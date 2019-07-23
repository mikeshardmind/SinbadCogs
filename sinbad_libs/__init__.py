import asyncio
import logging
from functools import wraps
from .tools import ToolBox


def extra_setup(func):
    @wraps(func)
    def _new_setup(bot):
        try:
            cog = ToolBox(bot)
            bot.add_cog(cog)
        except Exception:
            bot.remove_cog("Sinbad's Toolbox")
            bot.add_cog(cog)
        finally:  # Yes, I am intentionally returning in a finally statement.
            return func(bot)

    return _new_setup
