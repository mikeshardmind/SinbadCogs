from .guildwhitelist import GuildWhitelist


def setup(bot):
    bot.add_cog(GuildWhitelist(bot))
