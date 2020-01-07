from __future__ import annotations

import asyncio
import contextlib
import dataclasses
import io
import json
from datetime import datetime
from typing import List, Set, Union, AsyncIterator, Dict, Optional

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.modlog import create_case
from redbot.core.utils.chat_formatting import box, pagify

from .converters import SyndicatedConverter, ParserError, MemberOrID

GuildList = List[discord.Guild]
GuildSet = Set[discord.Guild]

_ = Translator("BanSync", __file__)


@cog_i18n(_)
class BanSync(commands.Cog):
    """
    synchronize your bans
    """

    __version__ = "2.2.5"

    def __init__(self, bot: Red, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.register_global(
            excluded_from_automatic=[],
            per_request_base_ratelimit=0.02,  # Approximately accurate.
            fractional_usage=0.5,
        )

    @commands.group()
    async def bansyncset(self, ctx: commands.Context):
        """
        Options for bansync
        """
        pass

    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    @bansyncset.command()
    async def automaticoptout(self, ctx: commands.Context):
        """
        This allows you to opt a server out of being selected for some actions

        The current things it will prevent:

        mjolnir|globalban
        bansync with automatic destinations
        syndicatebans with automatic destinations

        Things it will not prevent:

        bansync with an explicit choice to include the server.
        syndicatebans with automatic destinations
        """
        async with self.config.excluded_from_automatic() as exclusions:
            if ctx.guild.id in exclusions:
                return await ctx.send(
                    _("This server has already opted out of these actions.")
                )
            exclusions.append(ctx.guild.id)
        await ctx.tick()

    @checks.guildowner_or_permissions(administrator=True)
    @commands.guild_only()
    @bansyncset.command()
    async def automaticoptin(self, ctx: commands.Context):
        """
        This allows you to opt back into certain automatic actions.

        See `[p]help bansyncset automaticoptout` for more details
        """
        async with self.config.excluded_from_automatic() as exclusions:
            if ctx.guild.id not in exclusions:
                return await ctx.send(
                    _("This server has not opted out of these actions.")
                )
            exclusions.remove(ctx.guild.id)
        await ctx.tick()

    @commands.bot_has_permissions(ban_members=True, attach_files=True)
    @checks.admin_or_permissions(ban_members=True)
    @commands.guild_only()
    @commands.command(name="exportbans")
    async def exportbans(self, ctx: commands.Context):
        """
        Exports current servers bans to json
        """
        bans = await ctx.guild.bans()

        data = [b.user.id for b in bans]

        to_file = json.dumps(data).encode()
        fp = io.BytesIO(to_file)
        fp.seek(0)
        filename = f"{ctx.message.id}-bans.json"

        try:
            await ctx.send(
                ctx.author.mention, files=[discord.File(fp, filename=filename)]
            )
        except discord.HTTPException:
            await ctx.send(
                (
                    "You have a very interesting ban list to be too large to send, open an issue."
                )
            )

    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    @commands.guild_only()
    @commands.command(name="importbans")
    async def importbans(self, ctx: commands.Context):
        """
        Imports bans from json
        """

        if not ctx.message.attachments:
            return await ctx.send(
                _(
                    "You definitely need to supply me an exported ban list to be imported."
                )
            )

        fp = io.BytesIO()
        a = ctx.message.attachments[0]
        await a.save(fp)
        try:
            data = json.load(fp)
            if not isinstance(data, list) or not all(isinstance(x, int) for x in data):
                raise TypeError() from None
        except (json.JSONDecodeError, TypeError):
            return await ctx.send(_("That wasn't an exported ban list"))

        current_bans = await ctx.guild.bans()
        to_ban = set(data) - {b.user.id for b in current_bans}

        if not to_ban:
            return await ctx.send(
                _("That list doesn't contain anybody not already banned.")
            )

        async with ctx.typing():
            exit_codes = [
                await self.ban_or_hackban(
                    ctx.guild,
                    idx,
                    mod=ctx.author,
                    reason=f"Imported ban by {ctx.author}({ctx.author.id})",
                )
                for idx in to_ban
            ]

        if all(exit_codes):
            await ctx.message.add_reaction("\N{HAMMER}")
        elif not any(exit_codes):
            await ctx.send(_("You are not worthy"))
        else:
            await ctx.send(
                _(
                    "I got some of those, but other's couldn't be banned for some reason."
                )
            )

    @commands.command(name="bulkban")
    async def bulkban(self, ctx: commands.Context, *ids: int):
        """
        bulk global bans by id
        """
        rsn = f"Global ban authorized by {ctx.author}({ctx.author.id})"
        async with ctx.typing():
            results = {i: await self.targeted_global_ban(ctx, i, rsn) for i in set(ids)}

        if all(results.values()):
            await ctx.message.add_reaction("\N{HAMMER}")
        elif not any(results.values()):
            await ctx.send(_("You are not worthy"))
        else:
            await ctx.send(
                _(
                    "I got some of those, but other's couldn't be banned for some reason."
                )
            )

    async def can_sync(self, guild: discord.Guild, mod: discord.User) -> bool:
        """
        Determines if the specified user should
        be considered allowed to sync bans to the specified guild

        Parameters
        ----------
        guild: discord.Guild
        mod: discord.User

        Returns
        -------
        bool
            Whether the user is considered to be allowed to sync bans to the specified guild
        """
        if not guild.me.guild_permissions.ban_members:
            return False

        mod_member = guild.get_member(mod.id)
        if mod_member:
            if mod_member.guild_permissions.ban_members:
                return True
            if await self.bot.is_admin(mod_member):
                return True

        if await self.bot.is_owner(mod):
            return True

        return False

    async def ban_filter(
        self, guild: discord.Guild, mod: discord.User, target: discord.abc.Snowflake
    ) -> bool:
        """
        Determines if the specified user can ban another specified user in a guild

        Parameters
        ----------
        guild: discord.Guild
        mod: discord.User
        target: discord.User

        Returns
        -------
        bool
        """
        # TODO: rewrite more maintainibly.
        is_owner: bool = await self.bot.is_owner(mod)

        mod_member = guild.get_member(mod.id)
        if mod_member is None and not is_owner:
            return False

        # noted below lines contain a superflous condition covered above to help mypy

        can_ban: bool = guild.me.guild_permissions.ban_members
        if not is_owner and mod_member is not None:  # note
            can_ban &= mod_member.guild_permissions.ban_members

        target_m = guild.get_member(target.id)
        if target_m is not None and mod_member is not None:  # note
            can_ban &= guild.me.top_role > target_m.top_role or guild.me == guild.owner
            can_ban &= target_m != guild.owner
            if not is_owner:
                can_ban &= (
                    mod_member.top_role > target_m.top_role or mod_member == guild.owner
                )
        return can_ban

    async def ban_or_hackban(
        self,
        guild: discord.Guild,
        _id: int,
        *,
        mod: discord.User,
        reason: Optional[str] = None,
    ) -> bool:
        """

        Attempts to ban a user in a guild, supressing errors and just returning a success or fail

        Parameters
        ----------
        guild: discord.Guild
        _id: int
        mod: discord.User
        reason: :obj:`str`, optional

        Returns
        -------
        bool
            Whether the ban was successful
        """
        member: Optional[discord.abc.Snowflake] = guild.get_member(_id)
        reason = reason or _("Ban synchronization")
        if member is None:
            member = discord.Object(id=_id)
        if not await self.ban_filter(guild, mod, member):
            return False
        try:
            await guild.ban(member, reason=reason, delete_message_days=0)
        except discord.HTTPException:
            return False
        else:
            await create_case(
                self.bot, guild, datetime.utcnow(), "ban", member, mod, reason
            )

        return True

    async def guild_discovery(
        self, ctx: commands.Context, excluded: GuildSet
    ) -> AsyncIterator[discord.Guild]:
        """
        Fetches guilds which can be considered for synchronization in the current context (lazily)

        Parameters
        ----------
        ctx: commands.Context
        excluded: Set[discord.Guild]
            a set of guilds to be excluded from consideration

        Yields
        -------
        discord.Guild
            The next guild for use
        """
        for g in sorted(self.bot.guilds, key=lambda s: s.name):
            if g not in excluded and await self.can_sync(g, ctx.author):
                yield g

    async def interactive(self, ctx: commands.Context, excluded: GuildSet):
        guilds = [g async for g in self.guild_discovery(ctx, excluded)]
        if not guilds:
            return -1

        output = "\n".join(
            (
                *(f"{i}: {guild.name}" for i, guild in enumerate(guilds, 1)),
                _(
                    "Select a server to add to the sync list by number, "
                    "or -1 to stop adding servers"
                ),
            )
        )

        for page in pagify(output, delims=["\n"]):
            await ctx.send(box(page))

        def pred(m):
            return m.channel == ctx.channel and m.author == ctx.author

        try:
            message = await self.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            return -2
        else:
            try:
                message = int(message.content.strip())
                if message == -1:
                    return -1

                return guilds[message - 1]
            except (ValueError, IndexError):
                await ctx.send(_("That wasn't a valid choice"))
                return None

    async def process_sync(
        self,
        *,
        usr: discord.User,
        sources: GuildSet,
        dests: GuildSet,
        auto: bool = False,
        shred_ratelimits: bool = False,
    ) -> None:
        """
        Processes a synchronization of bans

        Parameters
        ----------
        usr: discord.User
            The user who authorized the synchronization
        sources: Set[discord.Guild]
            The guilds to sync from
        dests: Set[discord.Guild]
            The guilds to sync to
        auto: bool
            defaults as false, if provided destinations are augmented by the set of guilds which
            are not a source.
        shred_ratelimits: bool
            defaults false, allows for bypassing anti-choke measures.
        """

        bans: Dict[int, Set[discord.User]] = {}
        banlist: Set[discord.User] = set()

        if auto:
            exclusions: List[int] = await self.config.excluded_from_automatic()
            dests = {g for g in dests if g.id not in exclusions}

        guilds: GuildSet = sources | dests

        for guild in guilds:
            bans[guild.id] = set()
            try:
                g_bans = {x.user for x in await guild.bans()}
            except discord.HTTPException:
                pass
            else:
                bans[guild.id].update(g_bans)
                if guild in sources:
                    banlist.update(g_bans)

        tasks = []
        if shred_ratelimits and await self.bot.is_owner(usr):
            artificial_delay = 0.0
        else:
            base_limt: float = await self.config.per_request_base_ratelimit()
            fractional_usage: float = await self.config.fractional_usage()
            artificial_delay = (base_limt / fractional_usage) * len(dests)
        for guild in dests:
            to_ban = banlist - bans[guild.id]
            tasks.append(
                self.do_bans_for_guild(
                    guild=guild,
                    mod=usr,
                    targets=to_ban,
                    artificial_delay=artificial_delay,
                )
            )

        await asyncio.gather(*tasks)

    async def do_bans_for_guild(
        self,
        *,
        guild: discord.Guild,
        mod: discord.User,
        targets: Set[discord.User],
        artificial_delay: float,
    ):
        """
        This exists to speed up large syncs and consume ratelimits concurrently 
        """
        count = 0
        for target in targets:
            if await self.ban_filter(guild, mod, target):
                await self.ban_or_hackban(
                    guild, target.id, mod=mod, reason=_("Ban synchronization")
                )
                if artificial_delay:
                    await asyncio.sleep(artificial_delay)
                else:
                    count += 1
                    if count % 10:
                        # This is a safety measure to run infrequently
                        # but only if no per ban delay is there already.
                        await asyncio.sleep(0.1)

    @commands.command(name="bansync")
    async def ban_sync(self, ctx, auto=False):
        """
        syncs bans across servers
        """
        guilds: GuildSet = set()
        if not auto:
            while True:
                s = await self.interactive(ctx, guilds)
                if s == -1:
                    break
                if s == -2:
                    return await ctx.send(_("You took too long, try again later"))
                if s is not None:
                    guilds.add(s)

        elif auto is True:
            exclusions = await self.config.excluded_from_automatic()
            guilds = {
                g
                for g in self.bot.guilds
                if g.id not in exclusions and await self.can_sync(g, ctx.author)
            }

        if len(guilds) < 2:
            return await ctx.send(_("I need at least two servers to sync"))

        async with ctx.typing():
            await self.process_sync(usr=ctx.author, sources=guilds, dests=guilds)
        await ctx.tick()

    @checks.is_owner()
    @commands.command(name="syndicatebans")
    async def syndicated_bansync(self, ctx, *, query: SyndicatedConverter):
        """
        Push bans from one or more servers to one or more others.

        This is not bi-directional, use `[p]bansync` for that.

        Usage:
        `[p]syndicatebans --sources id(s) [--destinations id(s) | --auto-destinations]`
        """

        async with ctx.typing():
            await self.process_sync(**dataclasses.asdict(query))
        await ctx.tick()

    @syndicated_bansync.error
    async def syndicated_converter_handler(
        self, ctx, wrapped_error: commands.CommandError
    ):
        """
        Parameters
        ----------
        ctx: commands.Context
        wrapped_error: commmands.CommandError
        """

        error = getattr(wrapped_error, "original", wrapped_error)

        if isinstance(error, ParserError):
            if error.args:
                await ctx.send(error.args[0])
        else:
            await ctx.bot.on_command_error(ctx, wrapped_error, unhandled_by_cog=True)

    @commands.command(name="mjolnir", aliases=["globalban"])
    async def mjolnir(
        self, ctx, users: commands.Greedy[MemberOrID], *, rsn: str = None
    ):
        """
        Swing the heaviest of ban hammers
        """
        async with ctx.typing():
            banned = [
                await self.targeted_global_ban(ctx, user.id, rsn) for user in users
            ]
        if any(banned):
            await ctx.message.add_reaction("\N{HAMMER}")
        else:
            await ctx.send(_("You are not worthy"))

    @commands.command()
    async def unglobalban(
        self, ctx, users: commands.Greedy[MemberOrID], *, reason: str = None
    ):
        """
        To issue forgiveness.

        Or to fix a fuckup.
        """

        async def unban(guild, *user_ids, rsn=None):
            for user_id in user_ids:
                with contextlib.suppress(discord.HTTPException):
                    await guild.unban(discord.Object(id=user_id), reason=rsn)

        excluded: GuildSet = {
            g
            for g in self.bot.guilds
            if g.id in await self.config.excluded_from_automatic()
        }

        guilds = [g async for g in self.guild_discovery(ctx, excluded)]
        uids = [u.id for u in users]

        tasks = [unban(guild, *uids, rsn=reason) for guild in guilds]

        async with ctx.typing():
            await asyncio.gather(*tasks)

    async def targeted_global_ban(
        self, ctx: commands.Context, user: Union[discord.Member, int], rsn: str = None
    ) -> bool:
        """
        Bans a user everywhere the current moderator is allowed to,
        except the exclusions in config

        Parameters
        ----------
        ctx: commands.Context
            context the ban was issued from.
        user: Union[discord.Member, int]
            the target of the ban
        rsn: :obj:`str`, optional
            the reason to pass to discord for the ban.

        Returns
        -------
        bool
            Whether the user was banned from at least 1 guild by this action.
        """

        _id: int = getattr(user, "id", user)

        excluded: GuildSet = {
            g
            for g in self.bot.guilds
            if g.id in await self.config.excluded_from_automatic()
        }

        exit_codes = [
            await self.ban_or_hackban(guild, _id, mod=ctx.author, reason=rsn)
            async for guild in self.guild_discovery(ctx, excluded)
        ]

        return any(exit_codes)
