from .core import SuggestionBox

__red_end_user_data_statement__ = (
    "This cog stores data provided to it by command as needed for operation. "
    "As this data is for suggestions to be given from a user to a community, "
    "it is not reasonably considered end user data and will "
    "not be deleted except as required by Discord."
)


async def setup(bot):
    await bot.send_to_owners(
        "This cog still functions, but I suggest you leave and stop using Red. "
        "I was removed from Red for not wanting my work misrepresented by the "
        "organization, and stating what I would do *if* that continued. "
        'For how much Red and it\'s members go after people who " take credit" '
        "for their work, they sure were quick to dismiss mine. "
        "The cog will recieve no further updates, nor is anyone legally allowed to fork to update."
    )
    bot.add_cog(SuggestionBox(bot))
