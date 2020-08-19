from .guildwhitelist import GuildWhitelist

__red_end_user_data_statement__ = (
    "This cog persistently stores the minimum "
    "amount of data needed to maintain a server and server owner whitelist.\n"
    "It will not respect data deletion by end users as the data kept is the minimum "
    "needed for operation of an anti-abuse measure, nor can end users request "
    "their data from this cog since it only stores a discord ID.\n"
    "Discord IDs may occasionally be logged to a file as needed for audit purposes."
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
    bot.add_cog(GuildWhitelist(bot))
