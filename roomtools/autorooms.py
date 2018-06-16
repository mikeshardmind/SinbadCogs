from datetime import datetime, timedelta
import asyncio
import contextlib

import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.antispam import AntiSpam
from redbot.core.config import Config
from redbot.core import checks
from redbot.core.utils.chat_formatting import pagify

from .checks import aa_active


class AutoRooms:
    """
    Automagical Discord Voice Channels
    """

    __author__ = "mikeshardmind"
    __version__ = "6.0.0"

    antispam_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 30),
    ]

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(active=False, ownership=False)
        self.config.register_channel(
            ownership=None, gameroom=False, autoroom=False, clone=False
        )
        self._antispam = {}
        self.bot.loop.create_task(self._cleanup(load=True))

    async def on_resumed(self):
        await self._cleanup(load=True)

    async def _cleanup(self, *guilds: discord.Guild, load: bool = False):
        if load:
            await asyncio.sleep(10)

        if not guilds:
            guilds = self.bot.guilds

        for guild in guilds:
            for channel in guild.voice_channels:
                conf = self.config.channel(channel)
                if not await conf.clone():
                    continue
                if (
                    len(channel.members) == 0
                    and (channel.created_at + timedelta(seconds=2)) < datetime.utcnow()
                ):
                    try:
                        await channel.delete(reason="autoroom cleaning")
                    except discord.Forbidden:
                        break  # Don't bash our heads on perms
                    except discord.HTTPException:
                        pass
                    else:
                        await conf.clear()

    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """
        handles logic
        """

        if before.channel == after.channel:
            return

        if member.id not in self._antispam:
            self._antispam[member.id] = AntiSpam(self.antispam_intervals)
        if not self._antispam[member.id].spammy:
            if after.channel:
                if await self.config.guild(after.channel.guild).active():
                    conf = self.config.channel(after.channel)
                    if await conf.autoroom() or await conf.gameroom():
                        await self.generate_room_for(who=member, source=after.channel)

        if before.channel:
            await self._cleanup(before.channel.guild)

    async def generate_room_for(
        self, *, who: discord.Member, source: discord.VoiceChannel
    ):
        """
        makes autorooms
        """

        ownership = await self.config.channel(source).ownership()
        if ownership is None:
            ownership = await self.config.guild(source.guild).ownership()

        category = source.category

        editargs = {"bitrate": source.bitrate, "user_limit": source.user_limit}
        overwrites = {}
        for perm in source.overwrites:
            overwrites.update({perm[0]: perm[1]})
        if ownership:
            overwrites.update(
                {
                    who: discord.PermissionOverwrite(
                        manage_channels=True, manage_roles=True
                    )
                }
            )

        cname = None
        if await self.config.channel(source).gameroom():
            with contextlib.suppress(Exception):
                cname = who.activity.name
            if cname is None:
                cname = "???"
        else:
            cname = source.name

        try:
            chan = await source.guild.create_voice_channel(
                cname, category=category, overwrites=overwrites
            )
        except discord.Forbidden:
            await self.config.guild(source.guild).active.set(False)
            return
        except discord.HTTPException:
            pass
        else:
            await self.config.channel(chan).clone.set(True)
            if who.id not in self._antispam:
                self._antispam[who.id] = AntiSpam(self.antispam_intervals)
            self._antispam[who.id].stamp()
            await who.move_to(chan, reason="autoroom")
            await asyncio.sleep(0.5)
            await chan.edit(**editargs)
            # TODO: Consider creation using
            # discord.HTTP to avoid needing the edit

    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(autohelp=True)
    async def autoroomset(self, ctx: commands.Context):
        """
        Commands for configuring autorooms
        """
        pass

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="channelsettings")
    async def setchannelsettings(
        self, ctx: commands.Context, channel: discord.VoiceChannel
    ):
        """
        Interactive prompt for editing the autoroom behavior for specific
        channels
        """
        conf = self.config.channel(channel)

        if not await conf.autoroom():
            return await ctx.send("That isn't an autoroom")

        await ctx.send(
            (
                "Game rooms require the user joining to be playing "
                "a game, but get a base name of the game discord "
                "detects them playing. Game rooms also do not get"
                "anything prepended to their name."
                "\nIs this a game room?(y/n)"
            )
        )

        def mcheck(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            message = await self.bot.wait_for("message", check=mcheck, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("I can't wait forever, lets get to the next question.")
        else:
            if message.clean_content.lower()[:1] == "y":
                await conf.gameroom.set(True)
            else:
                await conf.gameroom.set(False)
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

        await ctx.send(
            (
                "There are three options for channel ownership\n"
                "1. Use the server default\n"
                "2. Override the default granting ownership\n"
                "3. Override the default denying ownership\n"
                "Please respond with the corresponding number to "
                "the desired behavior"
            )
        )

        try:
            message = await self.bot.wait_for("message", check=mcheck, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("I can't wait forever, lets get to the next question.")
        else:
            to_set = {"1": None, "2": True, "3": False}.get(
                message.clean_content[:1], None
            )
            await conf.ownership.set(to_set)
            await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")

    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="toggleactive")
    async def autoroomtoggle(self, ctx: commands.Context, val: bool = None):
        """
        turns autorooms on and off
        """
        if val is None:
            val = not await self.config.guild(ctx.guild).active()
        await self.config.guild(ctx.guild).active.set(val)
        await ctx.send(("Autorooms are now " + "activated" if val else "deactivated"))

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="makeclone")
    async def makeclone(self, ctx: commands.Context, channel: discord.VoiceChannel):
        """Takes a channel, turns that voice channel into an autoroom"""

        await self.config.channel(channel).autoroom.set(True)
        await ctx.tick()

    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="remclone")
    async def remclone(self, ctx, channel: discord.VoiceChannel):
        """Takes a channel, removes that channel from the clone list"""

        await self.config.channel(channel).clear()
        await ctx.tick()

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="listautorooms")
    async def listclones(self, ctx: commands.Context):
        """Lists the current autorooms"""
        clist = []
        for c in ctx.guild.voice_channels:
            if await self.config.channel(c).autoroom():
                clist.append("({0.id}) {0.name}".format(c))

        output = ", ".join(clist)
        for page in pagify(output):
            await ctx.send(page)

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="toggleowner")
    async def toggleowner(self, ctx: commands.Context, val: bool = None):
        """toggles if the creator of the autoroom owns it
        requires the "Manage Channels" permission
        Defaults to false"""
        if val is None:
            val = not await self.config.guild(ctx.guild).active()
        await self.config.guild(ctx.guild).active.set(val)
        await ctx.send(
            (
                "Autorooms are "
                + ("now owned " if val else "no longer owned ")
                + "by their creator"
            )
        )
