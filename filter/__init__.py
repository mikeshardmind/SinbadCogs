from .filter import Filter


def setup(bot):
    filter_cog = Filter(bot)
    bot.add_cog(filter_cog)
