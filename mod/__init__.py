import discord
from .mod import Mod


def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
    if discord.__version__ == "1.0.0a":
        bot.remove_listener(cog.on_member_update)
