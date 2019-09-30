import importlib
from . import bansync
from . import converters
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(converters)
    bansync = importlib.reload(bansync)
    bot.add_cog(bansync.BanSync(bot))
