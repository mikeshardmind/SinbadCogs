from redbot.core.bot import Red
from .mod import Mod

try:
    from redbot.core.errors import CogLoadError
except ImportError:
    CogLoadError = RuntimeError


def setup(bot: Red):
    if "Mod" in bot.cogs.keys():
        raise CogLoadError(
            "This replaces the mod cog. Unload it first if you want this."
        )
    bot.add_cog(Mod(bot))
