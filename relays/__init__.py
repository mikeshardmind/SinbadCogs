from . import relays

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    cog = relays.Relays(bot)
    bot.add_cog(cog)
    cog.init()
