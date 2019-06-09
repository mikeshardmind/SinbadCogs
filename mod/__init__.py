import discord
from .mod import Mod


def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
