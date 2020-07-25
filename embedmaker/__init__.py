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


def setup(bot):
    bot.add_cog(embedmaker.EmbedMaker(bot))
