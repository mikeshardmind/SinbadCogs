from .core import GuildJoinRestrict


def setup(bot):
    cog = GuildJoinRestrict(bot)
    bot.add_cog(cog)
    cog.init()
