import discord  # type: ignore
from redbot.core import checks
from redbot.core.commands import command, Cog, guild_only
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

    @Cog.listener(name="on_member_update")
    async def catcher(self, before, after):
        """
        Hmm?
        """

        maybe_custom = next(filter(lambda a: a.type == 4, after.activities), None)
        if not maybe_custom:
            return

        if INVITE_URL_RE.match(maybe_custom.state):
            self.bot.dispatch("sinbadcogs_detected_urlstatus", after)
            warn_channel_id = await self.config.guild(after.guild).channel()
            warn_channel = after.guild.get_channel(warn_channel_id)
            if warn_channel:
                await self.bot.send_filtered(
                    warn_channel,
                    filter_mass_mentions=True,
                    filter_all_links=False,
                    filter_invite_links=False,
                    content=(
                        f"Warning: {after.mention} has an invite url in status:"
                        f"\n\n{maybe_custom.state}"
                    ),
                )

    @checks.admin_or_permissions(manage_guild=True)
    @guild_only()
    @command(name="urlstatuslogset")
    async def setter(self, ctx, channel: discord.TextChannel = None):
        """
        Sets or clears the channel
        """
        if not channel:
            await self.config.guild(ctx.guild).channel.clear()
            await ctx.send("Not logging (use with a channel to set)")
        else:
            await self.config.guild(ctx.guild).channel.set(channel.id)
            await ctx.send(
                f"Logging custom statuses with invitelinks to : {channel.mention}"
            )
