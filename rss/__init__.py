try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


def setup(bot):
    try:
        from .core import RSS
    except ImportError:
        raise CogLoadError(
            "You need `feedparser` for this. Downloader *should* have handled this for you."
        )
    else:
        bot.add_cog(RSS(bot))
