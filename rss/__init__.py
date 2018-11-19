from redbot.core.errors import CogLoadError


def setup(bot):
    try:
        from .core import RSS
    except ImportError:
        raise CogLoadError(
            "You need feedparser for this. Downloader *should* have handled this for you."
        )
