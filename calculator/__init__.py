import sys
try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


def setup(bot):
    if sys.platform != "linux":
        raise CogLoadError("This doesn't work on your OS")
    else:
        from .calc import Calculator
        bot.add_cog(Calculator(bot))
