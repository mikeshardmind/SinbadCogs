import importlib
from . import bansync, converters
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(converters)
    module = importlib.reload(bansync)
    bot.add_cog(module.BanSync(bot))
