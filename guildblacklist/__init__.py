from . import guildblacklist


def setup(bot):
    bot.add_cog(guildblacklist.GuildBlacklist(bot))
