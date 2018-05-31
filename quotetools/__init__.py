from .quotetools import QuoteTools


def setup(bot):
    bot.add_cog(QuoteTools(bot))
