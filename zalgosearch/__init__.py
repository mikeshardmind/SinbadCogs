from .zalgosearch import ZalgoSearch


def setup(bot):
    bot.add_cog(ZalgoSearch(bot))