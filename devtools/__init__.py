from . import core
from .runner import Runner


def setup(bot):
    bot.add_cog(core.DevTools(bot))
    bot.add_cog(Runner(bot))
