from .cog import RenderTex
import sys


def setup(bot):
    if sys.version_info < (3, 6, 0):
        raise RuntimeError("Requires python >= 3.6")
    else:
        bot.add_cog(RenderTex(bot))
