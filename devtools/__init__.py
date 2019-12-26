from . import core


def setup(bot):
    bot.add_cog(core.DevTools(bot))
