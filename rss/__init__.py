from .core import RSS


def setup(bot):
    cog = RSS(bot)
    bot.add_cog(cog)
    cog.init()
