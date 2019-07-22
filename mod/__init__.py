import discord
from .mod import Mod
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
