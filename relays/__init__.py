from .relays import Relays


def setup(bot):
    bot.add_cog(Relays(bot))
