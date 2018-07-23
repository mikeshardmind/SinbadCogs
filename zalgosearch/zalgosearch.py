import re
import asyncio
from typing import Sequence

import discord
from redbot.core import commands, checks
from redbot.core.config import Config


from .zalgochars import ZALGOCHARS

ZALGO_REGEX = re.compile("|".join(ZALGOCHARS))


class ZalgoSearch:

    """
    Replaces display names using zalgo chars.
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.0b"

    def __init__(self, bot: "Red"):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(rename_to="zalgo is not allowed")

    async def _filter_by_zalgo(self, members: Sequence[discord.Member]):
        for member in members:
            if ZALGO_REGEX.match(member.display_name):
                yield member

    async def on_member_join(self, member: discord.Member):
        if member.guild.me.guild_permissions.manage_nicknames:
            if ZALGO_REGEX.match(member.display_name):
                await member.edit(nick=(await self.config.guild(member.guild).rename_to()))

    async def on_member_update(self, _before, member: discord.Member):
        if member.guild.me.guild_permissions.manage_nicknames:
            if ZALGO_REGEX.match(member.display_name):
                await member.edit(nick=(await self.config.guild(member.guild).rename_to()))

    @commands.guild_only()
    @checks.mod_or_permissions(manage_nicknames=True)
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.command(name="zalgocheck")
    async def zalgocheck(self, ctx: commands.Context, nick: str = None):
        """
        Mass remove zalgo names
        """

        if nick is None:
            nick = await self.config.guild(ctx.guild).rename_to()

        async for to_rename in self._filter_by_zalgo(ctx.guild.members):
            await to_rename.edit(nick=nick)
