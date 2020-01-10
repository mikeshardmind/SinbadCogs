from .filter import Filter
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    filter_cog = Filter(bot)
    bot.add_cog(filter_cog)
