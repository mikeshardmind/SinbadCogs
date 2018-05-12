from datetime import datetime, timedelta
import asyncio
import contextlib

import discord

from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.utils.antispam import AntiSpam
from redbot.core.config import Config
from redbot.core import checks

from .utils import send


class TempChannels:
    """
    Temporary Voice Channels
    """

    __author__ = "mikeshardmind"
    __version__ = "6.0.0"

    antispam_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 30)
    ]

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self._antispam = {}
        self.config.register_guild(active=False, category=None)
        self.config.register_channel(is_temp=False)
        self.bot.loop.create_task(self._cleanup(load=True))

    async def on_resumed(self):
        await self._cleanup(load=True)

    async def _cleanup(self, *guilds: discord.Guild, load: bool=False):
        if load:
            await asyncio.sleep(10)

        if not guilds:
            guilds = self.bot.guilds

        for guild in guilds:
            for channel in guild.voice_channels:
                conf = self.config.channel(channel)
                if not await conf.is_temp():
                    continue
                if (
                    len(channel.members) == 0
                    and (channel.created_at + timedelta(seconds=5))
                    < datetime.utcnow()
                ):
                    try:
                        await channel.delete(reason='temp channel cleaning')
                    except discord.Forbidden:
                        break  # Don't bash our heads on perms
                    except discord.HTTPException:
                        pass
                    else:
                        await conf.clear()

    def is_active_here(self):
        async def check(ctx: commands.Context):
            return await self.config.guild(ctx.guild).active()
        return commands.check(check)

    def isnt_spam(self):
        def check(ctx: commands.Context):
            if ctx.author.id in self._antispam:
                return not self._antispam[ctx.author.id].spammy()
            return True
        return commands.check(check)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_channels=True)
    @checks.admin_or_permissions(manage_channels=True)
    @commands.group(name='tempchannelset', aliases=['tmpcset'])
    async def tmpcset(self, ctx: commands.Context):
        """
        Temporary Channel Settings
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command()
    async def toggleactive(self, ctx: commands.Context, val: bool=None):
        """
        toggle (or explicitly set) whether temp channel creation is enabled
        """

        if val is None:
            val = not await self.config.guild(ctx.guild).active()
        await self.config.guild(ctx.guild).active.set(val)

        await send(
            ctx,
            'Temporary channel creation is now '
            + 'enabled' if val else 'disabled'
        )

    @checks.admin_or_permissions(manage_channels=True)
    @tmpcset.command(name='category')
    async def _category(
            self, ctx: commands.Context, cat: discord.CategoryChannel=None):
        """
        Sets the category for temporary channels

        Clears it if used without specifying one
        """

        if cat is None:
            await self.config.guild(ctx.guild).category.set(None)
            return await send(ctx, "Category cleared")

        await self.config.guild(ctx.guild).category.set(cat.id)
        await ctx.tick()

    @is_active_here()
    @isnt_spam()
    @commands.bot_has_permissions(manage_channels=True)
    @commands.command(name='tmpc')
    async def create_temp(self, ctx: commands.Context, *, channelname: str):
        """
        Creates a temporary channel
        """

        if not channelname:
            return await ctx.send_help()

        cat_id = await self.config.guild(ctx.guild).category()
        cat = discord.utils.get(ctx.guild.categories, id=cat_id)

        ow = discord.PermissionOverwrite(
            manage_channels=True, manage_roles=True
        )
        overwrites = {
            ctx.guild.me: ow,
            ctx.author: ow
        }

        try:
            created = await ctx.guild.create_voice_channel(
                channelname,
                category=cat,
                overwrites=overwrites
            )
        except discord.Forbidden:
            # how?
            await self.config.guild(ctx.guild).active.set(False)
            return
        except discord.HTTPException:
            # *sigh*
            return

        await self.config.channel(created).is_temp.set(True)
        if ctx.author.id not in self._antispam:
            self._antispam[ctx.author.id] = AntiSpam(self.antispam_intervals)
        self._antispam[ctx.author.id].stamp()

        with contextlib.suppress(Exception):
            current_voice = None
            current_voice = ctx.author.voice.channel
            if current_voice and ctx.guild.me.guild_permissions.move_members:
                await ctx.author.move(created)
