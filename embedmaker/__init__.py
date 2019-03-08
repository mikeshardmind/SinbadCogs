from . import embedmaker


def setup(bot):
    bot.add_cog(embedmaker.EmbedMaker(bot))
