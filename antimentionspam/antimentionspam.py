import discord
from redbot.core import commands, checks
from redbot.core.config import Config


class AntiMentionSpam:
    """removes mass mention spam"""

    __author__ = "mikeshardmind (Sinbad#0001)"
    __version__ = "1.0.2a"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(max_mentions=0)

    @commands.guild_only()
    @commands.group(autohelp=True)
    async def antimentionspam(self, ctx):
        """configuration settings for anti mention spam"""
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="max")
    async def set_max_mentions(self, ctx: commands.Context, number: int):
        """sets the maximum number of mentions allowed in a message
        a setting of 0 disables this check"""
        await self.config.guild(ctx.guild).max_mentions.set(number)
        message = (
            f"Max mentions set to {number}"
            if number > 0
            else "Mention filtering has been disabled"
        )
        await ctx.send(message)

    @checks.admin_or_permissions(manage_guild=True)
    @antimentionspam.command(name="autobantoggle", enabled=False, hidden=True)
    async def autobantoggle(self, ctx):
        """
        Toggle automatic ban for spam (default off)
        """
        pass

    async def on_message(self, message: discord.Message):
        if not isinstance(message.channel, discord.TextChannel):
            return
        guild = message.guild
        author = message.author
        channel = message.channel
        limit = await self.config.guild(guild).max_mentions()

        if len(message.mentions) < limit or limit <= 0:
            return

        if await self.is_immune(message):
            return

        if not channel.permissions_for(guild.me).manage_messages:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"Would have deleted message from {author.mention} "
                    f"for exceeding configured mention limit of: {limit}"
                )
            return

        try:
            await message.delete()
        except:
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

    async def is_immune(self, message):
        author = message.author
        guild = message.guild
        return (
            await self.bot.is_owner(message.author)
            or await self.bot.is_admin(message.author)
            or await self.bot.is_mod(message.author)
            or guild.me.top_role <= author.top_role
            or author == guild.owner
        )
