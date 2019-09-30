import importlib
from . import relays, helpers, relay
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    importlib.reload(helpers)
    importlib.reload(relay)
    relays = importlib.reload(relays)
    bot.add_cog(relays.Relays(bot))
