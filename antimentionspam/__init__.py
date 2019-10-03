import importlib

from . import antimentionspam
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    module = importlib.reload(antimentionspam)
    bot.add_cog(module.AntiMentionSpam(bot))
