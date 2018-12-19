
try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError

def setup(bot):

    try:
        assert bot.user.id == 275047522026913793
    except AssertionError:
        raise CogLoadError(
            "Installing a hidden cog, then trying to load it "
            "after the install message says it isn't ready? "
            " *waves finger* Naughty, Naughty."
        )
    else:
        from .scheduler import Scheduler
        bot.add_cog(Scheduler(bot))