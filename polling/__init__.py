from .polling import Polling


def setup(bot):
    bot.add_cog(Polling())
