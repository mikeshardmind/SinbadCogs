import importlib

from . import core, activity, converters
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(activity)
    importlib.reload(converters)
    module = importlib.reload(core)
    bot.add_cog(module.EconomyTrickle(bot))
