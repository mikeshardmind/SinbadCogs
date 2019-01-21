from .core import SuggestionBox


def setup(bot):
    bot.add_cog(SuggestionBox(bot))