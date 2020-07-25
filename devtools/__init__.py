from . import core
from .runner import Runner

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    bot.add_cog(core.DevTools(bot))
    bot.add_cog(Runner(bot))
