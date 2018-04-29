from datetime import datetime, timedelta
import asyncio
import contextlib

import discord
from discord.ext import commands

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils.antispam import AntiSpam
from redbot.core.config import Config
from redbot.core import checks

from .utils import send


class AutoRooms:
    """
    Automagical Discord Voice Channels
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
        self.config.register_guild(active=False, ownership=False)
        self.config.register_channel(
            ownership=None, gameroom=False, autoroom=False, clone=False
        )
        self._antispam = {}
        self.bot.loop.create_task(self._cleanup())

    async def on_resumed(self):
        await self._cleanup()

    async def _cleanup(self, *guilds: discord.Guild):
        if not guilds:
            guilds = self.bot.guilds

        for guild in guilds:
            for channel in guild.voice_channels:
                conf = self.config.channel(channel)
                if not await conf.clone():
                    continue
                if (
                    len(channel.members) == 0
                    and (channel.created_at + timedelta(seconds=2))
                    < datetime.utcnow()
                ):
                    try:
                        await channel.delete(reason='autoroom cleaning')
                    except discord.Forbidden:
                        break  # Don't bash our heads on perms
                    except discord.HTTPException:
                        pass
                    else:
                        await conf.clear()

    async def on_voice_state_update(
        self, member: discord.Member,
            before: discord.VoiceState, after: discord.VoiceState):
        """
        handles logic
        """

        if before.channel == after.channel:
            return

        if member.id in self._antispam \
                and not self._antispam[member.id].spammy():

            if await self.config.guild(after.channel.guild).active():
                conf = self.config.channel(after.channel)
                if await conf.autoroom():
                    await self.generate_autoroom_for(
                        who=member, source=after.channel
                    )
                elif await conf.gameroom():
                    await self.generate_gameroom_for(
                        who=member, source=after.channel
                    )

        if await self.config.channel(before.channel).clone():
            await self._cleanup(before.channel.guild)

    async def generate_room_for(
            self, *, who: discord.Member, source: discord.VoiceChannel):
        """
        makes autorooms
        """

        ownership = await self.config.channel(source).ownership()
        if ownership is None:
            ownership = await self.config.guild(source.guild).ownership()

        category = source.category

        editargs = {'bitrate': source.bitrate, 'user_limit': source.user_limit}
        overwrites = {}
        for perm in source.overwrites:
            overwrites.update({perm[0]: perm[1]})
        if ownership:
            overwrites.update(
                who,
                discord.PermissionOverwrite(
                    manage_channels=True,
                    manage_roles=True
                )
            )

        cname = None
        if await self.config.channel(source).gameroom():
            with contextlib.supress(Exception):
                cname = who.activity.name
            if cname is None:
                cname = '???'
        else:
            cname = source.name

        try:
            chan = await source.guild.create_voice_channel(
                cname,
                category=category,
                overwrites=overwrites
            )
        except discord.Forbidden:
            await self.config.guild(source.guild).active.set(False)
            return
        except discord.HTTPException:
            return
        else:
            await self.config.channel(chan).clone.set(True)
            if who.id not in self._antispam:
                self._antispam[who.id] = AntiSpam(self.antispam_intervals)
            self._antispam[who.id].stamp()
            await who.move_to(chan, reason="autoroom")
            await asyncio.sleep(0.5)
            await chan.edit(**editargs)
            # TODO: Consider discord.HTTP to avoid needing the edit
