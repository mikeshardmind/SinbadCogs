from . import guildwhitelist


def setup(bot):
    bot.add_cog(guildwhitelist.GuildWhitelist(bot))
