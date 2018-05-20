from .calc import Calculator
import sys


def setup(bot):
    if sys.platform != "linux":
        raise RuntimeWarning("This doesn't work on your OS")
    else:
        bot.add_cog(Calculator(bot))
