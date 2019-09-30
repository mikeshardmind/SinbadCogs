import importlib
from . import mod
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    mod = importlib.reload(mod)
    cog = mod.Mod(bot)
    bot.add_cog(cog)
