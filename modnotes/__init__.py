from redbot.core.errors import CogLoadError

try:
    import apsw
except ImportError:
    HAS_APSW = False
else:
    HAS_APSW = True


def setup(bot):
    if not HAS_APSW:
        raise CogLoadError(
            "This cog requires `apsw`. No support is provided for aquiring `apsw`."
        )
    else:
        from .modnotes import ModNotes

        bot.add_cog(ModNotes(bot))
