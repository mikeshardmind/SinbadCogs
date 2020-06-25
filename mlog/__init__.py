from .core import MLog


def setup(bot):
    cog = MLog(bot)
    bot.add_cog()
    cog.init()
