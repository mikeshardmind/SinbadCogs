from __future__ import annotations

from typing import cast

import discord
from redbot.core import checks, commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.common_filters import INVITE_URL_RE


class StatusWarn(commands.Cog):
    """
    Warns if a user is using a custom status with an invite in it
    """

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.register_guild(
            channel=None, warn_message="Warning: detected invite url in status:"
        )

    @commands.Cog.listener(name="on_member_update")
    async def catcher(self, before: discord.Member, after: discord.Member):
        """
        Hmm?
        """

        if before.activities == after.activities:
            return

        maybe_custom = cast(
            discord.Activity,
            next(filter(lambda a: a.type == 4, after.activities), None),
        )
        if not maybe_custom:
            return

        # Ugh, fuck discord for not letting `<>` supress invite links`
        neutered, count = INVITE_URL_RE.subn(
            r"[DISARMED LINK]: [\1  \2]", maybe_custom.state or ""
        )

        if count:
            self.bot.dispatch("sinbadcogs_detected_urlstatus", after)
            warn_channel_id = await self.config.guild(after.guild).channel()
            warn_message = await self.config.guild(after.guild).warn_message()
            warn_channel = after.guild.get_channel(warn_channel_id)
            if warn_channel:
                await self.bot.send_filtered(
                    warn_channel,
                    filter_mass_mentions=True,
                    filter_all_links=True,
                    filter_invite_links=True,
                    content=f"{warn_message}\n\n{after.mention} {neutered}",
                )

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="statuswarn")
    async def setter(self, ctx):
        """
        configuration for statuswarn
        """
        pass

    @setter.command(name="setchannel")
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """ Set the log channel """
        await self.config.guild(ctx.guild).channel.set(channel.id)
        await ctx.send(
            f"Logging custom statuses with invitelinks to : {channel.mention}"
        )

    @setter.command(name="unsetchannel")
    async def clear_channel(self, ctx):
        """ remove the logging channel """
        await self.config.guild(ctx.guild).channel.clear()
        await ctx.send("Not logging now.")
