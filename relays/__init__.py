import importlib

from . import relays, relay, helpers
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(helpers)
    importlib.reload(relay)
    module = importlib.reload(relays)
    bot.add_cog(module.Relays(bot))
