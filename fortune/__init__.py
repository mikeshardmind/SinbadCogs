from .fortune import Fortune

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    cog = Fortune(bot)
    bot.add_cog(cog)
