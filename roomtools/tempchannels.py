import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict

import discord
from redbot.core import checks, commands
from redbot.core.utils.antispam import AntiSpam

from .abcs import MixedMeta
from .checks import tmpc_active
from .converters import TempChannelConverter as ChannelData


class TempChannels(MixedMeta):
    """
    Temporary Voice Channels
    """

    @commands.Cog.listener("on_voice_state_update")
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

    async def tmpc_cleanup(self, guild: discord.Guild):

        for channel in guild.voice_channels:
            conf = self.tmpc_config.channel(channel)
            if not await conf.is_temp():
                continue
            if (not channel.members) and (
                channel.created_at + timedelta(seconds=20)
            ) < datetime.utcnow():
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
    async def tmpcset(self, ctx: commands.GuildContext):
        """
        Temporary Channel Settings
        """
        pass

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command()
    async def toggleactive(self, ctx: commands.GuildContext, val: bool = None):
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
        self, ctx: commands.GuildContext, *, cat: discord.CategoryChannel = None
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

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command(name="usecurrentcategory")
    async def _current_category(self, ctx: commands.GuildContext, yes_or_no: bool):
        """
        Sets temporary channels to be made in the same category as the command used.

        This will only be used if a categoy is not specified with `[p]tmpcset category`

        """
        await self.tmpc_config.guild(ctx.guild).current.set(yes_or_no)
        await ctx.tick()

    async def _delayed_check(self, guild: discord.Guild):
        await asyncio.sleep(30)
        await self.tmpc_cleanup(guild)

    @tmpc_active()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.command(name="tmpc")
    async def create_temp(
        self, ctx: commands.GuildContext, *, channeldata: ChannelData
    ):
        """
        Creates a temporary channel

        You can add `-u N` for some number `N` to add a user limit
        """
        if ctx.author.id not in self._antispam:
            self._antispam[ctx.author.id] = AntiSpam(self.antispam_intervals)
        if self._antispam[ctx.author.id].spammy:
            return

        channelname, user_limit = channeldata

        if not channelname:
            return await ctx.send_help()

        cat_id = await self.tmpc_config.guild(ctx.guild).category()
        if cat_id:
            cat = discord.utils.get(ctx.guild.categories, id=cat_id)
        elif await self.tmpc_config.guild(ctx.guild).current():
            cat = ctx.channel.category
        else:
            cat = None

        overwrites = dict(cat.overwrites) if cat else {}

        for target in (ctx.guild.me, ctx.author):
            p = overwrites.get(target, None) or discord.PermissionOverwrite()
            # Connect is NOT optional.
            p.update(manage_channels=True, manage_roles=True, connect=True)
            overwrites[target] = p

        opts: Dict[str, Any] = {"overwrites": overwrites}
        if cat:
            opts.update(category=cat)

        if user_limit:
            opts.update(user_limit=user_limit)

        try:
            created = await ctx.guild.create_voice_channel(channelname, **opts)
        except discord.Forbidden:
            # how?
            await self.tmpc_config.guild(ctx.guild).active.set(False)
            return
        except discord.HTTPException:
            # *sigh*
            return

        await self.tmpc_config.channel(created).is_temp.set(True)
        self._antispam[ctx.author.id].stamp()
        asyncio.create_task(self._delayed_check(ctx.guild))
        current_voice = ctx.author.voice.channel if ctx.author.voice else None
        if current_voice and ctx.guild.me.guild_permissions.move_members:
            await ctx.author.move_to(created)
