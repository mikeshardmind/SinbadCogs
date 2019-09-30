import importlib
from . import guildblacklist
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    guildblacklist = importlib.reload(guildblacklist)
    bot.add_cog(guildblacklist.GuildBlacklist(bot))
