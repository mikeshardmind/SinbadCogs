from .redirect import ChannelRedirect


def setup(bot):
    cog = ChannelRedirect(bot)
    bot.before_invoke(cog.before_invoke_hook)
    bot.add_cog(cog)
