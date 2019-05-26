from datetime import timedelta
from typing import Dict, TYPE_CHECKING

import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.utils.antispam import AntiSpam

if TYPE_CHECKING:
    from redbot.core.bot import Red

__all__ = ["AntiMentionSpam"]


class AntiMentionSpam(commands.Cog):
    """removes mass mention spam"""

    __version__ = "3.0.1"

    def __init__(self, bot: "Red", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: "Red" = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(
            max_mentions=0,
            threshold=0,
            interval=0,
            autoban=False,
            mute=False,
            warnmsg="",
            ban_single=False,
        )
        self.antispam: Dict[int, Dict[int, AntiSpam]] = {}

    @commands.guild_only()
    @commands.group(autohelp=True)
    async def antimentionspam(self, ctx: commands.Context):
        """
        Configuration settings for AntiMentionSpam
        """
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="max")
    async def set_max_mentions(self, ctx: commands.Context, number: int):
        """
        Sets the maximum number of mentions allowed in a message.

        A setting of 0 disables this check.
        """
        await self.config.guild(ctx.guild).max_mentions.set(number)
        message = (
            f"Max mentions set to {number}"
            if number > 0
            else "Mention filtering has been disabled"
        )
        await ctx.send(message)

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="maxinterval")
    async def set_max_interval_mentions(
        self, ctx: commands.Context, number: int, seconds: int
    ):
        """
        sets the maximum number of mentions allowed in a time period.

        Setting both to 0 will disable this check.
        """
        await self.config.guild(ctx.guild).threshold.set(number)
        await self.config.guild(ctx.guild).interval.set(seconds)
        message = (
            f"Max mentions set to {number} per {seconds}"
            if number > 0 and seconds > 0
            else "Mention interval filtering has been disabled"
        )
        self.antispam[ctx.guild.id] = {}
        await ctx.send(message)

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="autobantoggle")
    async def autobantoggle(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle automatic ban for spam (default off)
        """
        if enabled is None:
            enabled = not await self.config.guild(ctx.guild).autoban()

        await self.config.guild(ctx.guild).autoban.set(enabled)

        await ctx.send(f"Autoban mention spammers: {enabled}")

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="warnmsg")
    async def warnmessage(self, ctx: commands.Context, *, msg: str):
        """
        Sets the warn message. a message of "clear" turns the warn message off
        """

        if msg.lower() == "clear":
            msg = ""
        await self.config.guild(ctx.guild).warnmsg.set(msg)
        await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="singlebantoggle")
    async def singlebantog(self, ctx: commands.Context, enabled: bool = None):
        """
        Sets if single message limits allow a ban

        Default: False (interval threshold exceeding is required)
        """
        if enabled is None:
            enabled = not await self.config.guild(ctx.guild).ban_single()
        await self.config.guild(ctx.guild).ban_single.set(enabled)
        await ctx.send(f"Ban from single message settings: {enabled}")

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="mutetoggle")
    async def mute_toggle(self, ctx: commands.Context, enabled: bool = None):
        """
        Sets if a mute should be applied on exceeding limits set.
        """

        if enabled is None:
            enabled = not await self.config.guild(ctx.guild).mute()
        await self.config.guild(ctx.guild).mute.set(enabled)
        await ctx.send(f"Mute on exceeding set limits: {enabled}")

    async def process_intervals(self, message: discord.Message) -> bool:
        """

        Processes the interval check for messages.

        Parameters
        ----------
        message
            A message to process
        Returns
        -------
        bool
            If action was taken on against the author of the message.
        """
        guild = message.guild
        author = message.author

        data = await self.config.guild(guild).all()

        thresh, secs = data["threshold"], data["interval"]

        if not (thresh > 0 and secs > 0):
            return False

        if guild.id not in self.antispam:
            self.antispam[guild.id] = {}

        if author.id not in self.antispam[guild.id]:
            self.antispam[guild.id][author.id] = AntiSpam(
                [(timedelta(seconds=secs), thresh)]
            )

        # noinspection PyUnusedLocal
        for _m in message.mentions:
            self.antispam[guild.id][author.id].stamp()

        if self.antispam[guild.id][author.id].spammy:
            if not await self.is_immune(message):
                await self.maybe_punish(message)
                return True

        return False

    async def maybe_punish(
        self, message: discord.Message, single_message: bool = False
    ):
        """
        Handles the appropriate action on the author of a message based on settings.

        Parameters
        ----------
        message: discord.Message
        single_message: :obj:`bool`, optional
        """
        guild = message.guild
        target = message.author

        data = await self.config.guild(guild).all()

        ban = data["autoban"] and (data["ban_single"] or not single_message)
        warnmsg = data["warnmsg"]
        mute = data["mute"] and not ban

        if ban and guild.me.guild_permissions.ban_members:
            try:
                return await guild.ban(
                    discord.Object(id=target.id), reason="Mention Spam (Automated ban)"
                )
            except discord.HTTPException:
                pass

        if warnmsg and message.channel.permissions_for(guild.me).send_messages:
            try:
                await message.channel.send(f"{target.mention}: {warnmsg}")
            except discord.HTTPException:
                pass

        if mute:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).manage_roles:
                    overwrites = channel.overwrites_for(target)
                    overwrites.update(
                        send_messages=False, add_reactions=False, administrator=False
                    )
                    try:
                        await channel.set_permissions(
                            target,
                            overwrite=overwrites,
                            reason="Mention Spam (Automated mute)",
                        )
                    except discord.HTTPException:
                        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        guild = message.guild
        author = message.author
        channel = message.channel
        if not message.mentions:
            return

        if await self.is_immune(message):
            return

        limit = await self.config.guild(guild).max_mentions()

        if await self.process_intervals(message):
            return  # already punished

        if len(message.mentions) < limit or limit <= 0:
            return

        await self.maybe_punish(message, single_message=True)

        if not channel.permissions_for(guild.me).manage_messages:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"Would have deleted message from {author.mention} "
                    f"for exceeding configured mention limit of: {limit}"
                )
            return

        try:
            await message.delete()
        except discord.HTTPException:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"Attempt to delete message from {author.mention} "
                    f"for exceeding configured mention limit of: {limit} failed."
                )
        else:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"Deleted message from {author.mention} "
                    f"for exceeding configured mention limit of: {limit}"
                )

    async def is_immune(self, message: discord.Message) -> bool:
        """
        Determines if a message's author is immune from actions taken by this cog

        This is determined by a combination of if the bot can take action
        on the user and if they are considered immune from automated action.

        Parameters
        ----------
        message: discord.Message
            The message which triggered the check

        Returns
        -------
        bool
            Whether the user is or is not immune from the cog
        """
        author = message.author
        guild = message.guild
        if guild and (author == guild.owner or author.top_role >= guild.me.top_role):
            return True

        if await self.bot.is_owner(message.author):
            return True
        if await self.bot.is_automod_immune(message):
            return True

        return False
