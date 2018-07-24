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

    This only bothers replacing zalgo names which overflow vertically.
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.3b"

    def __init__(self, bot: "Red"):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(rename_to="zalgo is not allowed")
        self.running = set()
        self.seen_cache = set()

    async def _filter_by_zalgo(self, members: Sequence[discord.Member]):
        for member in members:
            if ZALGO_REGEX.match(member.display_name):
                yield member
            await asyncio.sleep(0.1)

    async def on_member_join(self, member: discord.Member):
        if member.guild.me.guild_permissions.manage_nicknames:
            if ZALGO_REGEX.match(member.display_name):
                await member.edit(nick=(await self.config.guild(member.guild).rename_to()))
            self.seen_cache.update((member.id, member.guild.id))

    async def on_member_update(self, m_before, member: discord.Member):
        if (
            (member.id, member.guild.id) in self.seen_cache 
            and member.display_name == m_before.display_name
        ):
            return
        if member.guild.me.guild_permissions.manage_nicknames:
            if ZALGO_REGEX.match(member.display_name):
                await member.edit(nick=(await self.config.guild(member.guild).rename_to()))

    @commands.guild_only()
    @checks.is_owner()
    @commands.bot_has_permissions(manage_nicknames=True)
    @commands.command(name="zalgocheck", hidden=True)
    async def zalgocheck(self, ctx: commands.Context, nick: str = None):
        """
        Mass remove zalgo names

        This is slow.
        """

        if ctx.guild.id in self.running:
            return await ctx.send("Already searching, please hold.")
        self.running.update(ctx.guild.id)
        if nick is None:
            nick = await self.config.guild(ctx.guild).rename_to()

        found_count = 0
        async for to_rename in self._filter_by_zalgo(ctx.guild.members):
            await to_rename.edit(nick=nick)
            found_count += 1
            
        if found_count > 0:
            await ctx.send(f"Found {found_count} users with zalgo names and renamed them")
        else:
            await ctx.send(
                "Hey, your members either aren't assholes, or the autofilter already caught them."
            )
        
        self.running.remove(ctx.guild.id)