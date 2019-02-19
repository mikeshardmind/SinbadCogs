from . import bansync


def setup(bot):
    bot.add_cog(bansync.BanSync(bot))
