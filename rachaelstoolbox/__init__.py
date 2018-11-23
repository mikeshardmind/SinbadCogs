try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


def setup(bot):
    try:
        assert bot.user.id == 275047522026913793
    except AssertionError:
        raise CogLoadError(
            "This isn't for you. "
            "It's in this repo for a combination of my own convienience, "
            "and for audit purposes."
        )
    else:
        from .management import Management

        bot.add_cog(Management(bot))
