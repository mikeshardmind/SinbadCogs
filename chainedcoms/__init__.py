from .chainedcoms import ChainedComs


def setup(bot):
    bot.add_cog(ChainedComs(bot))
