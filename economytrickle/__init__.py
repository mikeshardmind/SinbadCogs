import importlib
from . import core, converters, activity
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(activity)
    importlib.reload(converters)
    core = importlib.reload(core)
    bot.add_cog(core.EconomyTrickle(bot))
