from .modnotes import ModNotes

__red_end_user_data_statement__ = (
    "This cog stores data provided to it for "
    "the purpose of a permanent moderation note system. "
    "\nThis cog does not currently respect the data APIs and bot "
    "owners may need to handle data deletion requests for it manually, "
    "but they will be given notice in such cases."
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
    cog = ModNotes(bot)
    bot.add_cog(cog)
    cog.init()
