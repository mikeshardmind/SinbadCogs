from .core import DevTools


def setup(bot):
    bot.add_cog(DevTools(bot))
