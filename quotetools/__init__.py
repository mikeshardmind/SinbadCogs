from . import quotetools


def setup(bot):
    bot.add_cog(quotetools.QuoteTools(bot))
