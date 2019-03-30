from .filter import Filter
from redbot.core import commands


def setup(bot):
    filter_cog = Filter(bot)
    # This won't be needed after 3.1 of Red
    for attr_name in dir(filter_cog):
        x = getattr(filter_cog, attr_name, None)
        if isinstance(x, commands.Command):
            x.instance = filter_cog
            # setattr(filter_cog, attr_name, x)

    bot.add_cog(filter_cog)
