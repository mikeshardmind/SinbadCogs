from .guildblacklist import GuildBlacklist


def setup(bot):
    bot.add_cog(GuildBlacklist(bot))
