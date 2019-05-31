import discord
from redbot import version_info, VersionInfo
from redbot.core.errors import CogLoadError

from .scheduler import Scheduler
from .message import replacement_delete_messages


async def setup(bot):
    if version_info < VersionInfo.from_str("3.1.2"):
        raise CogLoadError(
            "Hey, this now depends on changes in Red 3.1.2."
            "\nGo update, it's a straight improvement from previously supported versions."
        )

    discord.TextChannel.delete_messages = replacement_delete_messages
    bot.add_cog(Scheduler(bot))
