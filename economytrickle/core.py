import asyncio
import contextlib
from datetime import datetime, timedelta
from collections import defaultdict

import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core import bank

from .activity import RecordHandler


class EconomyTrickle(commands.Cog):
    """
    Automatic Economy gains for active users
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(
            active=False,
            mode_is_blacklist=True,
            blacklisted_channels=[],
            whitelisted_channels=[],
            interval=5,
            level_xp_base=100,
            xp_lv_increase=50,
            maximum_level=None,
            xp_per_interval=10,
            econ_per_interval=20,
            bonus_per_level=5,
            maximum_bonus=None,
            extra_voice_xp=0,
            extra_message_xp=0,
            custom_level_table={},  # TODO
        )
        self.config.register_member(xp=0, level=0)
        self.recordhandler = RecordHandler()

        self.main_loop_task = bot.loop.create_task(self.main_loop())
        self.extra_tasks = []

        def __unload(self):
            self.main_loop_task.cancel()
            [t.cancel() for t in self.extra_tasks]

    async def on_message(self, message):
        if message.guild and await self.config.guild(message.guild).active():
            self.recordhandler.proccess_message(message)

    async def main_loop(self):

        minutes = defaultdict(int)

        while self is self.bot.get_cog(self.__class__.__name__):
            await asyncio.sleep(60)
            now = datetime.utcnow()

            data = await self.config.all_guilds()

            for g in self.bot.guilds:
                if g.id in data and data[g.id]["active"]:
                    minutes[g] += 1
                    if minutes[g] % data[g.id]["interval"]:
                        tsk = self.bot.loop.create_task(
                            self.do_rewards_for(g, now, data[g.id])
                        )
                        self.extra_tasks.append(tsk)

    async def do_rewards_for(self, guild: discord.Guild, now: datetime, data: dict):

        after = now - timedelta(minutes=data["interval"])

        if data["mode_is_blacklist"]:
            mpred = lambda m: m.channel.id not in data["blacklisted_channels"]

            def vpred(mem: discord.Member):
                with contextlib.suppress(AttributeError):
                    return (
                        mem.voice.channel.id not in data["blacklisted_channels"]
                        and not mem.bot
                    )

        else:
            mpred = lambda m: m.channel.id in data["whitelisted_channels"]

            def vpred(mem: discord.Member):
                with contextlib.suppress(AttributeError):
                    return (
                        mem.voice.channel.id in data["whitelisted_channels"]
                        and not mem.bot
                    )

        has_active_message = set(
            self.recordhandler.get_active_for_guild(
                guild=guild, after=after, message_check=mpred
            )
        )

        is_active_voice = {m for m in guild.members if vpred(m)}

        is_active = has_active_message | is_active_voice

        for member in is_active:

            # xp processing first
            xp = data["xp_per_interval"]
            if member in has_active_message:
                xp += data["extra_message_xp"]
            if member in is_active_voice:
                xp += data["extra_voice_xp"]

            xp = xp + await self.config.member(member).xp()
            await self.config.member(member).xp.set(xp)

            # level up: new mode in future.
            level, next_needed = 0, data["level_xp_base"]

            while xp >= next_needed:
                level += 1
                xp -= next_needed
                next_needed += data["xp_lv_increase"]

            if data["maximum_level"] is not None:
                level = min(data["maximum_level"], level)

            await self.config.member(member).level.set(level)

            # give economy

            to_give = data["econ_per_interval"]
            bonus = data["bonus_per_level"] * level
            if data["maximum_bonus"] is not None:
                bonus = min(data["maximum_bonus"], bonus)

            await bank.deposit_credits(member, to_give)

        # cleanup old message objects
        before = after - timedelta(seconds=1)
        self.recordhandler.clear_before(guild=guild, before=before)

    # Commands go here

    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="trickleset")
    async def ect(self, ctx):
        """
        Settings for economy trickle
        """
        pass

    @ect.command()
    async def active(self, ctx, active: bool):
        """
        Sets this as active (or not)
        """
        await self.config.guild(ctx.guild).active.set(active)
        await ctx.tick()
