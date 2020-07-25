from .core import SuggestionBox

__end_user_data_statement__ = (
    "This cog stores data provided to it by command as needed for operation. "
    "As this data is for suggestions to be given from a user to a community, "
    "it is not reasonably considered end user data and will not be deleted."
)


def setup(bot):
    bot.add_cog(SuggestionBox(bot))
