import importlib

from . import sanctuary


def setup(bot):
    module = importlib.reload(sanctuary)
    bot.add_cog(module.Sanctuary(bot))
