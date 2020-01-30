from .fortune import Fortune


def setup(bot):
    cog = Fortune(bot)
    bot.add_cog(cog)
