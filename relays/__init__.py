from . import relays


def setup(bot):
    cog = relays.Relays(bot)
    bot.add_cog(cog)
    cog.init()
