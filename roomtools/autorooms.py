from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Generator, cast

import discord
from redbot.core import checks, commands
from redbot.core.utils.antispam import AntiSpam
from redbot.core.utils.chat_formatting import pagify

from .abcs import MixedMeta
from .checks import aa_active

try:
    from redbot.core.commands import GuildContext
except ImportError:
    from redbot.core.commands import Context as GuildContext  # type: ignore


class AutoRooms(MixedMeta):
    """
    Automagical Discord Voice Channels
    """

    async def ar_cleanup(self, guild: discord.Guild):

        if await self.bot.cog_disabled_in_guild_raw(self.qualified_name, guild.id):
            return

        for channel in guild.voice_channels:
            conf = self.ar_config.channel(channel)
            if not await conf.clone():
                continue
            if (not channel.members) and (
                channel.created_at + timedelta(seconds=0.5)
            ) < datetime.utcnow():
                try:
                    await channel.delete(reason="autoroom cleaning")
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass
                else:
                    await conf.clear()

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update_ar(
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
        if (
            (not self._antispam[member.id].spammy)
            and after.channel
            and (await self.ar_config.guild(after.channel.guild).active())
        ):
            conf = self.ar_config.channel(after.channel)
            if await conf.autoroom() or await conf.gameroom():
                await self.generate_room_for(who=member, source=after.channel)

        if before.channel:
            await self.ar_cleanup(before.channel.guild)

    @staticmethod
    def _ar_get_overwrites(
        source: discord.VoiceChannel, *, who: discord.Member, ownership: bool
    ) -> dict:
        overwrites = dict(source.overwrites)
        if ownership:
            if who in overwrites:
                overwrites[who].update(manage_channels=True, manage_roles=True)
            else:
                overwrites.update(
                    {
                        who: discord.PermissionOverwrite(
                            manage_channels=True, manage_roles=True
                        )
                    }
                )
        # Note: Connect is not optional. Even with manage_channels,
        # the bot cannot edit or delete the channel
        # if it does not have this. This is *not* documented, and was discovered by trial
        # and error with a weird edge case someone had.
        if source.guild.me in overwrites:
            overwrites[source.guild.me].update(
                manage_channels=True, manage_roles=True, connect=True
            )
        else:
            overwrites.update(
                {
                    source.guild.me: discord.PermissionOverwrite(
                        manage_channels=True, manage_roles=True, connect=True
                    )
                }
            )

        return overwrites

    async def generate_room_for(
        self, *, who: discord.Member, source: discord.VoiceChannel
    ):
        """
        makes autorooms
        """
        # avoid object creation for comparison, it's slower
        # manage_channels + move_members + connect
        #  i.e 16 | 16777216 | = 17825808
        if not source.guild.me.guild_permissions.value & 17825808 == 17825808:
            return

        if await self.bot.cog_disabled_in_guild_raw(
            self.qualified_name, source.guild.id
        ):
            return

        cdata = await self.ar_config.channel(source).all(acquire_lock=False)

        ownership = cdata["ownership"]
        if ownership is None:
            ownership = await self.ar_config.guild(source.guild).ownership()

        category = source.category

        overwrites: dict = self._ar_get_overwrites(source, who=who, ownership=ownership)

        if cdata["gameroom"]:
            cname = "???"
            if activity := discord.utils.get(
                who.activities, type=discord.ActivityType.playing
            ):
                assert activity is not None, "mypy"  # nosec  # future remove
                cname = activity.name
        elif cdata["creatorname"]:
            cname = f"{source.name} {who.name}"
        # Stuff here might warrant a schema change to do this better.
        # Don't add this yet.
        # elif cdata["personalnamed"]:
        #     cname = f"{who}'s room"
        # elif cdata["randomname"]:
        #     pass   # TODO
        else:
            cname = source.name

        try:
            chan = await source.guild.create_voice_channel(
                cname, category=category, overwrites=overwrites
            )
        except discord.Forbidden:
            await self.ar_config.guild(source.guild).active.set(False)
            return
        except discord.HTTPException:
            pass
        else:
            await self.ar_config.channel(chan).clone.set(True)
            if who.id not in self._antispam:
                self._antispam[who.id] = AntiSpam(self.antispam_intervals)
            self._antispam[who.id].stamp()
            await who.move_to(chan, reason="autoroom")
            await asyncio.sleep(0.5)
            await chan.edit(bitrate=source.bitrate, user_limit=source.user_limit)
            # TODO:
            # discord.HTTP to avoid needing the edit
            # This extra API call is avoidable when working with the lower level tools.

    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(autohelp=True)
    async def autoroomset(self, ctx: GuildContext):
        """
        Commands for configuring autorooms
        """
        pass

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="channelsettings")
    async def setchannelsettings(
        self, ctx: GuildContext, channel: discord.VoiceChannel
    ):
        """
        Interactive prompt for editing the autoroom behavior for specific
        channels
        """
        conf = self.ar_config.channel(channel)

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
    async def autoroomtoggle(self, ctx: GuildContext, val: bool = None):
        """
        turns autorooms on and off
        """
        if val is None:
            val = not await self.ar_config.guild(ctx.guild).active()
        await self.ar_config.guild(ctx.guild).active.set(val)
        message = (
            "Autorooms are now activated" if val else "Autorooms are now deactivated"
        )
        await ctx.send(message)

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="makeclone")
    async def makeclone(self, ctx: GuildContext, channel: discord.VoiceChannel):
        """Takes a channel, turns that voice channel into an autoroom"""

        await self.ar_config.channel(channel).autoroom.set(True)
        await ctx.tick()

    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="remclone")
    async def remclone(self, ctx, channel: discord.VoiceChannel):
        """Takes a channel, removes that channel from the clone list"""

        await self.ar_config.channel(channel).clear()
        await ctx.tick()

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="listautorooms")
    async def listclones(self, ctx: GuildContext):
        """Lists the current autorooms"""
        clist = []
        for c in ctx.guild.voice_channels:
            if await self.ar_config.channel(c).autoroom():
                clist.append("({0.id}) {0.name}".format(c))

        output = ", ".join(clist)
        page_gen = cast(Generator[str, None, None], pagify(output))
        try:
            for page in page_gen:
                await ctx.send(page)
        finally:
            page_gen.close()

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="toggleowner")
    async def toggleowner(self, ctx: GuildContext, val: bool = None):
        """toggles if the creator of the autoroom owns it
        requires the "Manage Channels" permission
        Defaults to false"""
        if val is None:
            val = not await self.ar_config.guild(ctx.guild).ownership()
        await self.ar_config.guild(ctx.guild).ownership.set(val)
        message = (
            "Autorooms are now owned be their creator"
            if val
            else "Autorooms are no longer owned by their creator"
        )
        await ctx.send(message)

    @aa_active()
    @checks.admin_or_permissions(manage_channels=True)
    @autoroomset.command(name="creatorname")
    async def togglecreatorname(
        self, ctx: GuildContext, channel: discord.VoiceChannel, val: bool = None
    ):
        """Toggles if an autoroom will get the owner name after the channel name."""
        if val is None:
            val = not await self.ar_config.channel(channel).creatorname()
        await self.ar_config.channel(channel).creatorname.set(val)
        message = (
            "This channel will be generated by appending the creator's name"
            if val
            else "This channel will not be generated by appending the creator's name"
        )
        await ctx.send(message)
