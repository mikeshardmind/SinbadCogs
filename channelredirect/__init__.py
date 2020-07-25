from .redirect import ChannelRedirect

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


def setup(bot):
    cog = ChannelRedirect(bot)
    bot.add_cog(cog)
    bot.before_invoke(cog.before_invoke_hook)
