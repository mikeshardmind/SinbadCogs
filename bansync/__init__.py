import sys
from .bansync import BanSync


def setup(bot):
    bot.add_cog(BanSync(bot))
