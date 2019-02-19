from . import relays


def setup(bot):
    bot.add_cog(relays.Relays(bot))
