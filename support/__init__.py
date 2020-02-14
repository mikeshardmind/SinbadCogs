from __future__ import annotations

from redbot.core.bot import Red
from .core import Support


def setup(bot: Red):
    if bot.user.id == 275047522026913793:
        cog = Support(bot)
        bot.add_cog(cog)
        cog.init()
