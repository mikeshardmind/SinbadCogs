import importlib
from . import antimentionspam
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    antimentionspam = importlib.reload(antimentionspam)
    bot.add_cog(antimentionspam.AntiMentionSpam(bot))
