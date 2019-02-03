import discord
from .scheduler import Scheduler
from .message import replacement_delete_messages


def setup(bot):
    discord.TextChannel.delete_messages = replacement_delete_messages
    bot.add_cog(Scheduler(bot))
