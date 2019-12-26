from .core import ScreenshareAutoMod


def setup(bot):
    bot.add_cog(ScreenshareAutoMod(bot))
