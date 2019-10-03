import importlib

from . import guildblacklist
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    module = importlib.reload(guildblacklist)
    bot.add_cog(module.GuildBlacklist(bot))
