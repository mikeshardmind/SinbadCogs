from .modnotes import ModNotes

__end_user_data_statement__ = (
    "This cog stores data provided to it for "
    "the purpose of a permanent moderation note system. "
    "\nThis cog does not currently respect the data APIs and bot "
    "owners may need to handle data deletion requests for it manually, "
    "but they will be given notice in such cases."
)


def setup(bot):
    cog = ModNotes(bot)
    bot.add_cog(cog)
    cog.init()
