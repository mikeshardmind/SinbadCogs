import discord

from .message import replacement_delete_messages
from .scheduler import Scheduler

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users. "
    "It does store commands provided for intended later use along "
    "with the user ID of the person who scheduled it.\n"
    "Users may delete their own data without making a data request. "
    "This cog does not support a data deletion API fully yet, but will record "
    "data deletion requests to be proccessed when the "
    "functionality is fully supported."
)


def setup(bot):
    # Next line *does* work as intended. Mypy just hates it (see __slots__ use for why)
    discord.TextChannel.delete_messages = replacement_delete_messages  # type: ignore
    cog = Scheduler(bot)
    bot.add_cog(cog)
    cog.init()
