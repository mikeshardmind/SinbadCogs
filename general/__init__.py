from .general import General


def setup(bot):
    bot.add_cog(General(bot))
