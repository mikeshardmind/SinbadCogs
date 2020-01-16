from redbot.core.errors import CogLoadError


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

    cog = RSS(bot)
    bot.add_cog(cog)
    cog.init()
