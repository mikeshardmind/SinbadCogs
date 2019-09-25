from cog_shared.sinbad_libs import extra_setup
from .alias import AliasRewrite


@extra_setup
def setup(bot):
    bot.add_cog(AliasRewrite(bot))
