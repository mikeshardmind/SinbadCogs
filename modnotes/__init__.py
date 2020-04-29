from .modnotes import ModNotes


def setup(bot):
    cog = ModNotes(bot)
    bot.add_cog(cog)
    cog.init()
