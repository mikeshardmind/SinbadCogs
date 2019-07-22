import logging
from functools import wraps
from .tools import ToolBox


def extra_setup(func):
    @wraps(func)
    def _new_setup(bot):
        try:
            bot.add_cog(ToolBox(bot))
        finally:
            return func(bot)

    return _new_setup
