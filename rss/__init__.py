import importlib

from redbot.core.errors import CogLoadError
from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    try:
        from . import core, converters, cleanup

        importlib.reload(converters)
        importlib.reload(cleanup)
        module = importlib.reload(core)
    except ImportError:
        raise CogLoadError(
            "You need `feedparser` for this. Downloader *should* have handled this for you."
        )
    else:
        bot.add_cog(module.RSS(bot))
