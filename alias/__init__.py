import importlib
from cog_shared.sinbad_libs import extra_setup

from . import alias


@extra_setup
def setup(bot):
    module = importlib.reload(alias)
    bot.add_cog(module.AliasRewrite(bot))
