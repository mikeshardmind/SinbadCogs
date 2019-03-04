from datetime import datetime, timedelta
import asyncio
import contextlib

import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.antispam import AntiSpam
from redbot.core.config import Config
from redbot.core import checks

from .checks import tmpc_active
from .abcs import MixedMeta


class TempChannels(MixedMeta):
    """
    Temporary Voice Channels
    """

    async def on_voice_state_update_tmpc(
        self,
        _member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if before.channel == after.channel:
            return
        if before.channel:
            await self.tmpc_cleanup(before.channel.guild)

    async def tmpc_cleanup(self, *guilds: discord.Guild, load: bool = False):
        if load:
            await self.bot.wait_until_ready()
        await asyncio.sleep(0.5)

        if not guilds:
            guilds = self.bot.guilds

        for guild in guilds:
            for channel in guild.voice_channels:
                conf = self.tmpc_config.channel(channel)
                if not await conf.is_temp():
                    continue
                if (
                    len(channel.members) == 0
                    and (channel.created_at + timedelta(seconds=20)) < datetime.utcnow()
                ):
                    try:
                        await channel.delete(reason="temp channel cleaning")
                    except discord.Forbidden:
                        break  # Don't bash our heads on perms
                    except discord.HTTPException:
                        pass
                    else:
                        await conf.clear()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(name="tempchannelset", aliases=["tmpcset"], autohelp=True)
    async def tmpcset(self, ctx: commands.Context):
        """
        Temporary Channel Settings
        """
        pass

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command()
    async def toggleactive(self, ctx: commands.Context, val: bool = None):
        """
        toggle (or explicitly set) whether temp channel creation is enabled
        """

        if val is None:
            val = not await self.tmpc_config.guild(ctx.guild).active()
        await self.tmpc_config.guild(ctx.guild).active.set(val)

        await ctx.send(
            ("Temporary channel creation is now " + "enabled" if val else "disabled")
        )

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command(name="category")
    async def _category(
        self, ctx: commands.Context, *, cat: discord.CategoryChannel = None
    ):
        """
        Sets the category for temporary channels

        Clears it if used without specifying one
        """

        if cat is None:
            await self.tmpc_config.guild(ctx.guild).category.set(None)
            return await ctx.send("Category cleared")

        await self.tmpc_config.guild(ctx.guild).category.set(cat.id)
        await ctx.tick()

    @tmpc_active()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.command(name="tmpc")
    async def create_temp(self, ctx: commands.Context, *, channelname: str):
        """
        Creates a temporary channel
        """
        if ctx.author.id not in self._antispam:
            self._antispam[ctx.author.id] = AntiSpam(self.antispam_intervals)
        if self._antispam[ctx.author.id].spammy:
            return

        if not channelname:
            return await ctx.send_help()

        cat_id = await self.tmpc_config.guild(ctx.guild).category()
        cat = discord.utils.get(ctx.guild.categories, id=cat_id)
        overwrites = dict(cat.overwrites) if cat else {}

        for target in (ctx.guild.me, ctx.author):
            p = overwrites.get(target, None) or discord.PermissionOverwrite()
            # Connect is NOT optional.
            p.update(manage_channel=True, manage_roles=True, connect=True)
            overwrites[target] = p

        try:
            created = await ctx.guild.create_voice_channel(
                channelname, category=cat, overwrites=overwrites
            )
        except discord.Forbidden:
            # how?
            await self.tmpc_config.guild(ctx.guild).active.set(False)
            return
        except discord.HTTPException:
            # *sigh*
            return

        await self.tmpc_config.channel(created).is_temp.set(True)
        self._antispam[ctx.author.id].stamp()

        with contextlib.suppress(Exception):
            current_voice = None
            current_voice = ctx.author.voice.channel
            if current_voice and ctx.guild.me.guild_permissions.move_members:
                await ctx.author.move(created)
