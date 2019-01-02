import asyncio
import json
import io
from typing import List, Set

import discord

from redbot.core.utils.chat_formatting import box, pagify
from redbot.core import commands, checks
from redbot.core.i18n import Translator, cog_i18n
from .converters import SyndicatedConverter

GuildList = List[discord.Guild]
GuildSet = Set[discord.Guild]

T_ = Translator("BanSync", __file__)
_ = lambda s: s  # So that unguarded strings below are not modified in place.

# Strings go here for ease of modification with pygettext
INTERACTIVE_PROMPT_I = _(
    "Select a server to add to the sync list by number, "
    'or enter "-1" to stop adding servers'
)

ASYNCIOTIMEOUT = _("You took too long, try again later")

INVALID_CHOICE = _("That wasn't a valid choice")

TOO_FEW_CHOSEN = _("I need at least two servers to sync")

BAN_REASON = _("Ban synchronization")

BANS_SYNCED = _("Bans have been synchronized across selected servers")

UNWORTHY = _("You are not worthy")

PARTIAL_SUCCESS = _(
    "I got some of those, but other's couldn't be banned for some reason."
)

TOO_MANY_BANS_WAT = _(
    "Contact me. You have a very interesting ban list to be too large to send."
)

EXPECTED_FILE = _(
    "You definitely need to supply me an exported ban list to be imported."
)

INVALID_FILE = _("That wasn't an exported ban list")

ALL_ALREADY_BANNED = _("That list doesn't contain anybody not already banned.")

BANMOJI = "\U0001f528"

_ = T_


# pylint: disable=E1133
# pylint doesn't seem to handle implied async generators properly yet
@cog_i18n(_)
class BanSync(commands.Cog):
    """
    synchronize your bans
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.2.1"
    __flavor_text__ = "Ban export/import json."

    def __init__(self, bot):
        self.bot = bot

    @commands.bot_has_permissions(ban_members=True, attach_files=True)
    @checks.admin_or_permissions(ban_members=True)
    @commands.guild_only()
    @commands.command(name="exportbans")
    async def exportbans(self, ctx):
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
            await ctx.send(TOO_MANY_BANS_WAT)

    @commands.bot_has_permissions(ban_members=True)
    @checks.admin_or_permissions(ban_members=True)
    @commands.guild_only()
    @commands.command(name="importbans")
    async def importbans(self, ctx):
        """
        Imports bans from json
        """

        if not ctx.message.attachments:
            return await ctx.send(EXPECTED_FILE)

        fp = io.BytesIO()
        a = ctx.message.attachments[0]
        await a.save(fp)
        try:
            data = json.load(fp)
            assert isinstance(data, list)
            assert all(isinstance(x, int) for x in data)
        except (json.JSONDecodeError, AssertionError):
            return await ctx.send(INVALID_FILE)

        current_bans = await ctx.guild.bans()
        to_ban = set(data) - {b.user.id for b in current_bans}

        if not to_ban:
            return await ctx.send(ALL_ALREADY_BANNED)

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
            await ctx.message.add_reaction(BANMOJI)
        elif not any(exit_codes):
            await ctx.send(UNWORTHY)
        else:
            await ctx.send(PARTIAL_SUCCESS)

    @commands.command(name="bulkban")
    async def bulkban(self, ctx, *ids: int):
        """
        bulk global bans by id
        """
        rsn = f"Global ban authorized by {ctx.author}({ctx.author.id})"
        async with ctx.typing():
            results = {
                i: await self.targeted_global_ban(ctx, str(i), rsn) for i in set(ids)
            }

        if all(results.values()):
            await ctx.message.add_reaction(BANMOJI)
        elif not any(results.values()):
            await ctx.send(UNWORTHY)
        else:
            await ctx.send(PARTIAL_SUCCESS)

    @commands.command(name="bansyncdebuginfo", hidden=True)
    async def debuginfo(self, ctx):
        await ctx.send(
            box(
                "Author: {a}\nBan Sync Version: {ver} ({flavor})".format(
                    a=self.__author__, ver=self.__version__, flavor=self.__flavor_text__
                )
            )
        )

    async def can_sync(self, g: discord.Guild, u: discord.User):
        user_allowed = False
        m = g.get_member(u.id)
        if m:
            user_allowed |= m.guild_permissions.ban_members
        settings = self.bot.db.guild(g)
        _arid = await settings.admin_role()
        user_allowed |= await self.bot.is_owner(u)
        user_allowed |= any(r.id == _arid for r in u.roles)
        bot_allowed = g.me.guild_permissions.ban_members
        return user_allowed and bot_allowed

    async def ban_filter(
        self, g: discord.Guild, mod: discord.user, target: discord.user
    ):
        if await self.bot.is_owner(mod):
            can_ban = True

        mod = g.get_member(mod.id)
        if mod is None:
            return False

        can_ban = (
            mod.guild_permissions.ban_members and g.me.guild_permissions.ban_members
        )
        target = g.get_member(target.id)
        if target is not None:
            can_ban &= g.me.top_role > target.top_role or g.me == g.owner
            can_ban &= target != g.owner
            can_ban &= mod.top_role > target.top_role or mod == g.owner
        return can_ban

    async def ban_or_hackban(
        self, guild: discord.Guild, _id: int, *, mod: discord.User, reason: str = None
    ):
        member = guild.get_member(_id)
        reason = reason or BAN_REASON
        if member is None:
            member = discord.Object(id=_id)
        if not await self.ban_filter(guild, mod, member):
            return False
        try:
            await guild.ban(member, reason=reason, delete_message_days=0)
        except discord.HTTPException:
            return False
        else:
            return True

    async def guild_discovery(self, ctx: commands.context, picked: GuildSet):
        for g in sorted(self.bot.guilds, key=lambda s: s.name):
            if g not in picked and await self.can_sync(g, ctx.author):
                yield g

    async def interactive(self, ctx: commands.context, picked: GuildSet):
        output = ""
        guilds = [g async for g in self.guild_discovery(ctx, picked)]
        if len(guilds) == 0:
            return -1
        for i, guild in enumerate(guilds, 1):
            output += "{}: {}\n".format(i, guild.name)
        output += INTERACTIVE_PROMPT_I
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
                else:
                    guild = guilds[message - 1]
            except (ValueError, IndexError):
                await ctx.send(INVALID_CHOICE)
                return None
            else:
                return guild

    async def process_sync(
        self, *, usr: discord.User, sources: GuildSet, dests: GuildSet
    ):

        bans: dict = {}
        banlist = set()

        guilds = sources | dests

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

        for guild in dests:
            to_ban = banlist - bans[guild.id]
            for maybe_ban in to_ban:
                if await self.ban_filter(guild, usr, maybe_ban):
                    await self.ban_or_hackban(
                        guild, maybe_ban.id, mod=usr, reason=BAN_REASON
                    )

    @commands.command(name="bansync")
    async def ban_sync(self, ctx, auto=False):
        """
        syncs bans across servers
        """
        guilds = set()
        if not auto:
            while True:
                s = await self.interactive(ctx, guilds)
                if s == -1:
                    break
                if s == -2:
                    return await ctx.send(ASYNCIOTIMEOUT)
                elif s is None:
                    continue
                else:
                    guilds.add(s)
        elif auto is True:
            guilds = {g for g in self.bot.guilds if await self.can_sync(g, ctx.author)}

        if len(guilds) < 2:
            return await ctx.send(TOO_FEW_CHOSEN)

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
            await self.process_sync(**query)
        await ctx.tick()

    @commands.command(name="mjolnir", aliases=["globalban"])
    async def mjolnir(self, ctx, user: str, *, rsn: str = None):
        """
        Swing the heaviest of ban hammers
        """
        banned = await self.targeted_global_ban(ctx, user, rsn)
        if banned:
            await ctx.message.add_reaction(BANMOJI)
        else:
            await ctx.send(UNWORTHY)

    async def targeted_global_ban(
        self, ctx: commands.Context, user: str, rsn: str = None
    ):
        conv = commands.UserConverter()
        try:
            x = await conv.convert(ctx, user)
        except Exception:
            _id = int(user)
        else:
            _id = x.id

        exit_codes = [
            await self.ban_or_hackban(guild, _id, mod=ctx.author, reason=rsn)
            async for guild in self.guild_discovery(ctx, set())
        ]

        return any(exit_codes)
