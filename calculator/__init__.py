from .calc import Calculator
import sys


def setup(bot):
    if sys.platorm != 'linux':
        raise RuntimeWarning("This doesn't work on your OS")
    else:
        bot.add_cog(Calculator(bot))
