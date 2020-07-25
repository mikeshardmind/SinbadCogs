from .guildblacklist import GuildBlacklist

__end_user_data_statement__ = (
    "This cog persistently stores the minimum "
    "amount of data needed to maintain a server and server owner blacklist.\n"
    "It will not respect data deletion by end users as the data kept is the minimum "
    "needed for operation of an anti-abuse measure, nor can end users request "
    "their data from this cog since it only stores a discord ID.\n"
    "Discord IDs may occasionally be logged to a file as needed for audit purposes."
)


def setup(bot):
    bot.add_cog(GuildBlacklist(bot))
