from redbot.cogs.filter import Filter as _Filter
import discord
from typing import Union, Set
import asyncio
from redbot.core import commands, checks


try:
    import re2
except ImportError:
    re2 = None

import re


class Filter(_Filter, commands.Cog):
    def __init__(self, bot):
        super().__init__(bot)
        # self._additional_pattern_cache = defaultdict(list)
        self._regex_atom_pattern_cache: dict = {}
        self.settings.register_guild(regex_atoms=[])
        self.settings.register_channel(regex_atoms=[])

    @commands.guild_only()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.group(name="regexfilter")
    async def rfg(self, ctx):
        """ Commands for managing the regex filter """
        pass

    @rfg.command(name="addatom")
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
                self._regex_atom_pattern_cache[(ctx.guild, None)] = valid_compile
                atoms.append(atom)

        await ctx.tick()

    @rfg.command(name="removeatom")
    async def rfg_guild_add(self, ctx: commands.Context, *, atom: str):
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

    @rfg.group(name="channel")
    async def rfg_channel(self, ctx: commands.Context):
        """ Commands for managing regex per channel """
        pass

    @rfg_channel.command(name="addatom")
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
                self._regex_atom_pattern_cache[(ctx.guild, ctx.channel)] = valid_compile
                atoms.append(atom)

        await ctx.tick()

    @rfg_channel.command(name="removeatom")
    async def rfg_channel_add(self, ctx: commands.Context, *, atom: str):
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

    def invalidate_atom(
        self, guild: discord.Guild, channel: discord.TextChannel = None
    ):
        """ Invalidate a cached pattern built from atoms"""
        self._regex_atom_pattern_cache.pop((guild, channel), None)

    async def filter_hits(
        self, text: str, server_or_channel: Union[discord.Guild, discord.TextChannel]
    ) -> Set[str]:

        try:
            guild = server_or_channel.guild
            channel = server_or_channel
        except AttributeError:
            guild = server_or_channel
            channel = None

        hits = set()

        try:
            pattern = self.pattern_cache[(guild, channel)]
        except KeyError:
            word_list = set(await self.settings.guild(guild).filter())
            if channel:
                word_list |= set(await self.settings.channel(channel).filter())

            if word_list:
                pattern = re.compile(
                    "|".join(rf"\b{re.escape(w)}\b" for w in word_list), flags=re.I
                )
            else:
                pattern = None
            self.pattern_cache[(guild, channel)] = pattern

        if pattern:
            hits |= set(pattern.findall(text))

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
            hits |= set(pattern.findall(text))

        return hits
