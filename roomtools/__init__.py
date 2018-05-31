from .autorooms import AutoRooms
from .tempchannels import TempChannels


def setup(bot):
    for cog in (AutoRooms, TempChannels):
        bot.add_cog(cog(bot))
