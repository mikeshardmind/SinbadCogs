from . import statuswarn


def setup(bot):
    bot.add_cog(statuswarn.StatusWarn(bot))
