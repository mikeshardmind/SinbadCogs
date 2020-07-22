from redbot.core.errors import CogLoadError

from .core import MLog


def setup(bot):
    if bot.user.id != 275047522026913793:
        raise CogLoadError(
            "Hey, stop that. "
            "This was listed as WIP *and* hidden, "
            "*and* warned you about *liabilities.* "
            "Last warning, stop it. Stop trying to "
            "log messages without understanding how badly this can go."
        )
    cog = MLog(bot)
    bot.add_cog(cog)
    cog.init()
