from .core import EconomyTrickle


def setup(bot):
    bot.add_cog(EconomyTrickle(bot))
