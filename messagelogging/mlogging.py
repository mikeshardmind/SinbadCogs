from typing import List, Optional, Dict

import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from .logs import get_logger


class MessageLogging(commands.Cog):
    """
    Logs messages

    Warning: This may not be compliant with various regions data policies.
    This should be used only in compliance with data policies.

    This uses per guild rotating file handlers, so messages are not stored indefinitely.

    This is also really really abusing some things to get this working quickly
        so ya know, not ready for public use and hidden as such.
    """

    def __init__(self, bot):
        self.bot = bot
        self.logs = {}
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(active=False)

    async def on_message(self, message: discord.Message):

        if not (message.guild and await self.config.guild(message.guild).active()):
            return

        if message.guild.id not in self.logs:
            self.logs[message.guild.id] = get_logger(f"{message.guild.id}")

        content = message.content or ""
        content = content.replace("\n", "\\n")
        self.logs[message.guild.id].info(
            f"{message.author}({message.author.id}): {content}"
        )

    @checks.guildowner()
    @commands.guild_only()
    @commands.command(name="togglelogging")
    async def toglog(self, ctx):
        """
        Toggles logging
        """

        status = not await self.config.guild(ctx.guild).active()
        await self.config.guild(ctx.guild).active.set(status)
        await ctx.send(f"Logging {'is' if status else 'is not'} enabled")
