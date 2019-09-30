try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError

from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    try:
        from .core import RSS
    except ImportError:
        raise CogLoadError(
            "You need `feedparser` for this. Downloader *should* have handled this for you."
        )
    else:
        bot.add_cog(RSS(bot))
