import importlib
from . import quotetools, helpers
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(helpers)
    quotetools = importlib.reload(quotetools)
    bot.add_cog(quotetools.QuoteTools(bot))
