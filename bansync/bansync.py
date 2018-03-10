import asyncio
from typing import List

import discord
from discord.ext import commands

from redbot.core.i18n import CogI18n
from redbot.core.utils.chat_formatting import box, pagify

GuildList = List[discord.Guild]
_ = CogI18n("BanSync", __file__)

# Strings go here for ease of modification with pygettext
INTERACTIVE_PROMPT_I = _("Select a server to add to the sync list by number, "
                         "or enter \"-1\" to stop adding servers")

ASYNCIOTIMEOUT = _("You took too long, try again later")

INVALID_CHOICE = _("That wasn't a valid choice")

TOO_FEW_CHOSEN = _("I need at least two servers to sync")

BAN_REASON = _("Ban synchronization")

BANS_SYNCED = _("Bans have been synchronized across selected servers")

UNWORTHY = _("You are not worthy")

BANMOJI = '\U0001f528'


class BanSync:
    """
    synchronize your bans
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '1.0.1a'

    def __init__(self, bot):
        self.bot = bot
        self._owner = None

    @commands.command(name='bansyncdebuginfo', hidden=True)
    async def debuginfo(self, ctx):
        await ctx.send(
            box(
                "Author: {a}\nBan Sync Version: {v}".format(
                    a=self.__author__, v=self.__version__
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
        user_allowed |= u.id == (await self.bot.application_info()).owner.id
        user_allowed |= any(r.id == _arid for r in u.roles)
        bot_allowed = g.me.guild_permissions.ban_members
        return user_allowed and bot_allowed

    def ban_filter(self, g: discord.Guild, u: discord.user, t: discord.user):
        m = g.get_member(u.id)
        if m is None and u.id != self._owner.id:
            return False
        elif u.id == self._owner.id:
            can_ban = True
        else:
            can_ban = m.guild_permissions.ban_members \
                and g.me.guild_permissions.ban_members
        target = g.get_member(t.id)
        if target is not None:
            can_ban &= g.me.top_role > target.top_role
        return can_ban

    async def ban_or_hackban(self, guild: discord.Guild, _id: int, **kwargs):
        member = guild.get_member(_id)
        reason = kwargs.get('reason', BAN_REASON)
        if member is None:
            member = discord.Object(id=_id)
        try:
            await guild.ban(member, reason=reason, delete_message_days=0)
        except (discord.Forbidden, discord.HTTPException) as e:
            return False
        else:
            return True  # TODO: modlog hook

    async def guild_discovery(self, ctx: commands.context, picked: GuildList):
        for g in sorted(self.bot.guilds, key=lambda s: s.name):
            if g not in picked and await self.can_sync(g, ctx.author):
                yield g

    async def interactive(self, ctx: commands.context, picked: GuildList):
        output = ""
        guilds = self.guild_discovery(ctx, picked)
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
            message = await self.bot.wait_for(
                'message', check=pred, timeout=60
            )
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

    async def process_sync(self, usr: discord.User, guilds: GuildList):
        bans = {}

        for guild in guilds:
            try:
                g_bans = [x.user for x in await guild.bans()]
            except (discord.Forbidden, discord.HTTPException) as e:
                pass
            else:
                bans[guild.id] = g_bans[:]

        for guild in guilds:
            to_ban = []
            for k, v in bans.items():
                to_ban.extend(
                    [m for m in v if m not in bans[guild.id]
                     and self.ban_filter(guild, usr, m)]
                )

            for x in to_ban:
                await self.ban_or_hackban(
                    guild,
                    x.id,
                    mod=usr,
                    reason=BAN_REASON
                )

    @commands.command(name='bansync')
    async def ban_sync(self, ctx, auto=False):
        """
        syncs bans across servers
        """
        guilds = []
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
                    guilds.append(s)
        elif auto is True:
            guilds = [g for g in self.bot.guilds
                      if await self.can_sync(g, ctx.author)]

        if len(guilds) < 2:
            return await ctx.send(TOO_FEW_CHOSEN)

        await self.process_sync(ctx.author, guilds)
        await ctx.tick()

    @commands.command(name="mjolnir", aliases=['globalban'])
    async def mjolnir(self, ctx, user: str, *, rsn: str=None):
        """
        Swing the heaviest of ban hammers
        """
        conv = commands.UserConverter()
        try:
            x = await conv.convert(ctx, user)
        except Exception:
            _id = int(user)
        else:
            _id = x.id

        exit_codes = [
            await self.ban_or_hackban(
                guild,
                _id,
                mod=ctx.author,
                reason=rsn
            ) for guild in await self.guild_discovery(ctx, [])
        ]

        if any(exit_codes):
            await ctx.message.add_reaction(BANMOJI)
        else:
            await ctx.send(UNWORTHY)
