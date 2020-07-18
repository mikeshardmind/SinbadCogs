import warnings
from .core import RSS

warnings.filterwarnings("once", category=DeprecationWarning, module="feedparser")


def setup(bot):
    cog = RSS(bot)
    bot.add_cog(cog)
    cog.init()
