from .filter import Filter


def setup(bot):
    bot.add_cog(Filter(bot))
