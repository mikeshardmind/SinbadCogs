from .mod import Mod


def setup(bot):
    cog = Mod(bot)
    bot.add_cog(cog)
    bot.remove_listener(cog.on_member_update)
