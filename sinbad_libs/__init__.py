import asyncio
import logging
from functools import wraps
from .tools import ToolBox


def extra_setup(func):
    if asyncio.iscoroutinefunction(func):

        @wraps(func)
        async def _new_async_setup(bot):
            try:
                bot.add_cog(ToolBox(bot))
            finally:
                return await func(bot)

        return _new_async_setup

    else:

        @wraps(func)
        def _new_setup(bot):
            try:
                bot.add_cog(ToolBox(bot))
            finally:
                return func(bot)

        return _new_setup
