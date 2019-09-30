from . import embedmaker
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    bot.add_cog(embedmaker.EmbedMaker(bot))
