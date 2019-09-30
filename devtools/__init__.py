import importlib
from . import core
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    core = importlib.reload(core)
    bot.add_cog(core.DevTools(bot))
