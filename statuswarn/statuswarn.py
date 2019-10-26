import discord  # type: ignore
from redbot.core import checks
from redbot.core.commands import command, group, Cog, guild_only
from redbot.core.config import Config
from redbot.core.bot import Red
from redbot.core.utils.common_filters import INVITE_URL_RE


class StatusWarn(Cog):
    """
    Warns if a user is using a custom status with an invite in it
    """

    def __init__(self, bot):
        self.bot: Red = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.register_guild(channel=None)
        self.custom_message = None

    @Cog.listener(name="on_member_update")
    async def catcher(self, before, after):
        """
        Hmm?
        """

        if before.activities == after.activities:
            return

        maybe_custom = next(filter(lambda a: a.type == 4, after.activities), None)
        if not maybe_custom:
            return

        if INVITE_URL_RE.match(maybe_custom.state):
            self.bot.dispatch("sinbadcogs_detected_urlstatus", after)
            warn_channel_id = await self.config.guild(after.guild).channel()
            warn_channel = after.guild.get_channel(warn_channel_id)
            if warn_channel:
                msg = self.custom_message or "Warning: detected invite url in status:"
                await self.bot.send_filtered(
                    warn_channel,
                    filter_mass_mentions=True,
                    filter_all_links=False,
                    filter_invite_links=False,
                    content=f"{msg}\n\n{after.mention} {maybe_custom.state}",
                )

    @checks.admin_or_permissions(manage_guild=True)
    @guild_only()
    @group(name="statuswarn")
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
        await ctx.send("Not logging (use with a channel to set)")
