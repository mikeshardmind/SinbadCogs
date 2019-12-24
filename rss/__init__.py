try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError

from cog_shared.sinbad_libs import extra_setup


@extra_setup
def setup(bot):
    try:
        import feedparser
    except ImportError:
        raise CogLoadError(
            "You need `feedparser` for this. Downloader *should* have handled this for you."
        )
    try:
        import discordtextsanitizer
    except ImportError:
        raise CogLoadError(
            "You need `discord-text-sanitizer` for this. Downloader *should* have handled this for you."
        )

    from .core import RSS

    bot.add_cog(RSS(bot))
