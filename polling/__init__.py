from . import polling


def setup(bot):
    bot.add_cog(polling.Polling())
