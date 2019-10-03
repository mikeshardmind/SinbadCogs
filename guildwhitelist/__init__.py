import importlib

from . import guildwhitelist
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    module = importlib.reload(guildwhitelist)
    bot.add_cog(module.GuildWhitelist(bot))
