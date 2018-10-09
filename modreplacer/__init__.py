from redbot.core.bot import Red
from .mod import Mod


def setup(bot: Red):
    bot.get_cog("Core")._unload("Mod")
    bot.add_cog(Mod(bot))
