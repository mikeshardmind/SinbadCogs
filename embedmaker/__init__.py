from .embedmaker import EmbedMaker


def setup(bot):
    bot.add_cog(EmbedMaker(bot))
