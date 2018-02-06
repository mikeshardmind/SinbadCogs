import asyncio
from typing import List, Union

import discord
from discord.ext import commands

from redbot.core.i18n import CogI18n
from redbot.core import Config
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

BANMOJI = '\U0001f528'


class BanSync:
    """
    synchronize your bans
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '0.0.1u'

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

    async def __before_invoke(self, ctx):
        if self._owner is None:
            self._owner = (await self.bot.application_info()).owner

    def can_sync(self, g: discord.Guild, u: discord.User):
        user_allowed = False
        m = g.get_member(u.id)
        if m:
            user_allowed |= m.guild_permissions.ban_members
        user_allowed |= u.id == self._owner.id
        bot_allowed = g.me.guild_permissions.ban_members
        return user_allowed and bot_allowed

    def ban_filter(self, g: discord.Guild, u: discord.user, t: discord.user):
        m = g.get_member(u.id)
        if m is None and u.id != self._owner.id:
            return False
        can_ban = m.guild_permissions.ban_members \
            and g.me.guild_permissions.ban_members
        target = g.get_member(t.id)
        if target is not None:
            can_ban &= g.me.top_role > target.top_role \
                and m.top_role > target.top_role
        return can_ban

    async def ban_or_hackban(self, guild: discord.Guild, _id: int, **kwargs):
        member = guild.get_member(_id)
        if member is None:
            member = discord.Object(id=_id)
        try:
            await guild.ban(member, reason=BAN_REASON)
        except (discord.Forbidden, discord.HTTPException) as e:
            pass  # TODO: Decide what the hell to do with this.
        else:
            pass  # TODO: modlog hook

    def server_discovery(self, ctx: commands.context, picked: GuildList):
        return sorted([
            g for g in self.bot.guilds
            if self.can_sync(g, ctx.author)
            and g not in picked
        ], key=lambda s: s.name)

    async def interactive(self, ctx: commands.context, picked: GuildList):
        output = ""
        servers = self.server_discovery(ctx, picked)
        if len(servers) == 0:
            return -1
        for i, server in enumerate(servers, 1):
            output += "{}: {}\n".format(i, server.name)
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
                    server = servers[message - 1]
            except (ValueError, IndexError):
                await ctx.send(INVALID_CHOICE)
                return None
            else:
                return server

    async def process_sync(self, usr: discord.User, guilds: GuildList):
        bans = {}

        for guild in guilds:
            try:
                bans = [x.user for x in (await guild.bans())]
            except (discord.Forbidden, discord.HTTPException) as e:
                pass
            else:
                bans[guild.id] = bans

        for guild in guilds:
            to_ban = []
            for k, v in bans.items():
                to_ban.extend(
                    [m for m in v if m not in bans[guild.id]
                     and self.ban_filter(guild, usr, m)]
                )

            for x in to_ban():
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
        servers = []
        if not auto:
            while True:
                s = await self.interactive(ctx, servers)
                if s == -1:
                    break
                if s == -2:
                    return await ctx.send(ASYNCIOTIMEOUT)
                elif s is None:
                    continue
                else:
                    servers.append(s)
        elif auto is True:
            servers = [g for g in self.bot.guilds
                       if self.can_sync(g, ctx.author)]

        if len(servers) < 2:
            return await ctx.send(TOO_FEW_CHOSEN)

        await self.process_sync(servers)
        await ctx.tick()

    @commands.command(name="globalban", aliases=['mjolnir'])
    async def mjolnir(self, ctx, user: Union[discord.User, int], *, rsn: str):
        """
        Swing the heaviest of ban hammers
        """
        _id = user.id if isinstance(user, discord.User) else user

        for guild in self.server_discovery(ctx, []):
            await self.ban_or_hackban(
                guild,
                _id,
                mod=ctx.author,
                reason=rsn
            )
        await ctx.message.add_reaction(BANMOJI)
