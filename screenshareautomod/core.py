import discord
from redbot.core import commands, checks
from redbot.core.config import Config

AFK = 1
KICK = 2
MUTE = 3


class ScreenshareAutoMod(commands.Cog):
    """
    Configureable cog to automod screenshare usage.
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.1"
    __flavor_text__ = "UGH, discord doesn't remove this or make it respect the new system."

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(active=False, action=0)
        self.config.register_channel(exclude=False)

    @commands.Cog.listener()
    async def vc_update(self, member, before, after):
        channel = after.channel
        guild = member.guild
        if channel and after.self_video:
            await self.maybe_punish_screenshare(guild, channel, member)

    async def maybe_punish_screenshare(self, guild, channel, member):
        if not await self.config.guild(guild).active():
            return

        if await self.config.channel(channel).exclude():
            return

        if await self.bot.is_automod_immune(member):
            return

        # and now we have confirmed they aren't imune.

        action = await self.config.guild(guild).action()

        if action == AFK:
            afk_channel = guild.afk_channel
            if guild.me.guild_permissions.move_members and afk_channel:
                try:
                    await member.move_to(afk_channel, reason="Screenshare use.")
                except discord.HTTPException:
                    pass

        elif action == KICK:
            if guild.me.top_role > member.top_role:
                if guild.me.guild_permissions.kick_members:
                    if member != guild.owner:
                        try:
                            await member.kick(reason="Screenshare use.")
                        except discord.Forbidden:  # Still possible 2FA issue
                            pass
                        except discord.HTTPException:  # or even API issues.
                            pass
        return
        # TODO: Below
        # if action == MUTE:
        #    if guild.me.top_role > member.top_role:
        #        if guild.me.guild_permissions.mute_members:
        #
        #
        #            if member != guild.owner:
        #                 pass

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="screensharemod")
    async def ssg(self, ctx):
        """
        Stuff for configuring this cog
        """
        pass

    @ssg.command()
    async def toggleactive(self, ctx):
        """
        Toggles if this cog is active
        """

        val = not await self.config.guild(ctx.guild).active()
        await self.config.guild(ctx.guild).active.set(val)
        await ctx.send(
            f"Automoderation of screenshare {'is' if val else 'is not'} active"
        )

    @ssg.command()
    async def action(self, ctx, action):
        """
        Sets the action to take on users violating the no-screenshare policy.

        Valid actions are "afk", "kick", or "none"
        """

        try:
            action_id = {"afk": AFK, "kick": KICK, "none": 0}[action.lower()]
        except KeyError:
            return await ctx.send_help()

        await self.config.guild(ctx.guild).action.set(action_id)
        await ctx.tick()
