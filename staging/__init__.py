from .staging import Staging


def setup(bot):
    bot.add_cog(Staging(bot))
