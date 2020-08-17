from . import embedmaker

__red_end_user_data_statement__ = (
    "This cog stores data provided by users "
    "for the express purpose of redisplaying.\n"
    "It does not store user data which was not "
    "provided through a command.\n"
    "Users may remove their own content "
    "without making a data removal request.\n"
    "This cog will also remove data through a data request."
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
    bot.add_cog(embedmaker.EmbedMaker(bot))
