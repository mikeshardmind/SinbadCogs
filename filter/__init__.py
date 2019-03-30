from .filter import Filter
from redbot.core import commands

def setup(bot):
    filter_cog = Filter(bot)
    bot.add_cog(filter_cog)
