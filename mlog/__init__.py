from redbot.core.errors import CogLoadError

from .core import MLog

__red_end_user_data_statement__ = (
    "This cog logs messages and does not respect the data APIs. "
    "Bot owners have been warned against loading this cog as it is a work in progress. "
    "Bot owners will recieve notice of attempts to delete data and it is on them to handle "
    "this manually at the current time."
)


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
