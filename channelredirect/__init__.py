from .redirect import ChannelRedirect


def setup(bot):
    cog = ChannelRedirect(bot)
    bot.add_cog(cog)
