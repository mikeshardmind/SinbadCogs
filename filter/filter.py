try:
    import re2
except ImportError:
    re2 = None

import re
from typing import Union, Set

import discord
from redbot.core import checks, Config, commands
from redbot.core.bot import Red
from redbot.cogs.filter import Filter as _Red_Filter


class Filter(_Red_Filter):
    """Filter unwanted words and phrases from text channels."""

    def __init__(self, bot: Red):
        self._regex_atom_pattern_cache: dict = {}
        super().__init__()
        self.settings = Config.get_conf(self, 4766951341)
        default_guild_settings = {
            "filter": [],
            "filterban_count": 0,
            "filterban_time": 0,
            "filter_names": False,
            "filter_default_name": "John Doe",
            "regex_atoms": [],
        }
        default_member_settings = {"filter_count": 0, "next_reset_time": 0}
        default_channel_settings = {"filter": [], "regex_atoms": []}
        self.settings.register_guild(**default_guild_settings)
        self.settings.register_member(**default_member_settings)
        self.settings.register_channel(**default_channel_settings)

    def cog_unload(self):
        self.register_task.cancel()

    def invalidate_atom(
        self, guild: discord.Guild, channel: discord.TextChannel = None
    ):
        """ Invalidate a cached pattern built from atoms"""
        self._regex_atom_pattern_cache.pop((guild, channel), None)
        if channel is None:
            for k in self.pattern_cache.keys():
                if guild in k:
                    self.pattern_cache.pop(k, None)

    async def filter_hits(
        self, text: str, server_or_channel: Union[discord.Guild, discord.TextChannel]
    ) -> Set[str]:

        try:
            guild = server_or_channel.guild
            channel = server_or_channel
        except AttributeError:
            guild = server_or_channel
            channel = None

        hits: Set[str] = set()

        hits |= await super().filter_hits(text, server_or_channel)

        try:
            pattern = self._regex_atom_pattern_cache[(guild, channel)]
        except KeyError:
            atoms = set(await self.settings.guild(guild).regex_atoms())
            if channel:
                atoms |= set(await self.settings.channel(channel).regex_atoms())

            if atoms:
                try:
                    str_pattern = "|".join(atoms)
                    pattern = re2.compile(str_pattern)
                except re.error:
                    pattern = None

                self._regex_atom_pattern_cache[(guild, channel)] = pattern

        if pattern:
            match = pattern.search(text)
            if match:
                hits.add(match.string)

        return hits

    @commands.check(lambda ctx: bool(re2))
    @commands.group(name="re2filter")
    async def regex_filter(self, ctx):
        """ Filter for regex """
        pass

    @commands.check(lambda ctx: bool(re2))
    @regex_filter.group(name="channel")
    async def regex_filter_channel(self, ctx):
        """ Channel specific regex """
        pass

    @commands.check(lambda ctx: bool(re2))
    @regex_filter.command(name="addatom")
    async def rfg_guild_add(self, ctx: commands.Context, *, atom: str):
        """ 
        Attempts to add a regex atom. 
        
        All atoms must be joinable by `|` for this to be valid
        """

        async with self.settings.guild(ctx.guild).regex_atoms() as atoms:
            if atom in atoms:
                return await ctx.send("This atom is already contained")
            atom_set = set(atoms)
            atom_set.add(atom)
            try:
                valid_compile = re2.compile("|".join(atoms))
            except re.error:
                return await ctx.send("This results in an invalid pattern")
            else:
                self.invalidate_atom(guild=ctx.guild)
                atoms.append(atom)

        await ctx.tick()

    @commands.check(lambda ctx: bool(re2))
    @regex_filter.command(name="removeatom")
    async def rfg_guild_rem(self, ctx: commands.Context, *, atom: str):
        """ 
        removes a regex atom. 
        """
        async with self.settings.guild(ctx.guild).regex_atoms() as atoms:
            if atom in atoms:
                self.invalidate_atom(guild=ctx.guild)
                atoms.remove(atom)
            else:
                return await ctx.send("This wasn't an atom")

        await ctx.tick()

    @commands.check(lambda ctx: bool(re2))
    @regex_filter_channel.command(name="addatom")
    async def rfg_channel_add(self, ctx: commands.Context, *, atom: str):
        """ 
        Attempts to add a regex atom. 
        
        All atoms must be joinable by `|` for this to be valid
        """

        async with self.settings.channel(ctx.channel).regex_atoms() as atoms:
            if atom in atoms:
                return await ctx.send("This atom is already contained")
            atom_set = set(atoms)
            atom_set.add(atom)
            try:
                valid_compile = re2.compile("|".join(atoms))
            except re.error:
                return await ctx.send("This results in an invalid pattern")
            else:
                self.invalidate_atom(guild=ctx.guild)
                atoms.append(atom)

        await ctx.tick()

    @commands.check(lambda ctx: bool(re2))
    @regex_filter_channel.command(name="removeatom")
    async def rfg_channel_rem(self, ctx: commands.Context, *, atom: str):
        """ 
        removes a regex atom. 
        """
        async with self.settings.channel(ctx.channel).regex_atoms() as atoms:
            if atom in atoms:
                self.invalidate_atom(guild=ctx.guild, channel=ctx.channel)
                atoms.remove(atom)
            else:
                return await ctx.send("This wasn't an atom")

        await ctx.tick()
