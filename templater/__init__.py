from redbot.core.errors import CogLoadError

from .core import Templater


def setup(bot):
    if bot.user.id != 275047522026913793:
        raise CogLoadError(
            "No. This one has security implications and "
            "should not be loaded prior to me signing off on it being ready."
        )
    bot.add_cog(Templater())
