from .mentionhelp import MentionHelp


def setup(bot):
    cog = MentionHelp(bot)
    bot.add_cog(cog)
    cog.init()
