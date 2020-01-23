from .redirect import ChannelRedirect


def setup(bot):
    cog = ChannelRedirect(bot)
    bot.add_cog(cog)
    bot.before_invoke(cog.before_invoke_hook)
