import warnings

from .core import RSS

warnings.filterwarnings("once", category=DeprecationWarning, module="feedparser")

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    cog = RSS(bot)
    bot.add_cog(cog)
    cog.init()
