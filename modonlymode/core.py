from typing import Optional

import discord
from discord.utils import SnowflakeList
from redbot.core import Config, checks, commands
from redbot.core.bot import Red


class ModOnlyMode(commands.Cog):
    """
    Cog to limit the bot to mods and higher.
    """

    __version__ = "339.1.0"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot: Red, config: Config, cache: SnowflakeList):
        self.bot: Red = bot
        self.cache: SnowflakeList = cache
        self.config: Config = config

    @classmethod
    async def setup(cls, bot: Red):
        config = Config.get_conf(None, 78631113035100160, cog_name="ModOnlyMode")
        config.register_guild(active=False)

        active = (
            guild_id
            for guild_id, data in (await config.all_guilds())
            if data.get("active", False)
        )

        cache = SnowflakeList(active)

        cog = cls(bot, config, cache)
        bot.add_cog(cog)

    async def __permissions_hook(self, ctx: commands.Context) -> Optional[bool]:
        if ctx.guild and self.cache.has(ctx.guild.id):
            assert isinstance(ctx.author, discord.Member), "mypy"  # nosec
            if not await self.bot.is_mod(ctx.author):
                return False

        return None

    @checks.admin()
    @commands.guild_only()
    @commands.command()
    async def enablemodonlymode(self, ctx: commands.GuildContext):
        """
        Makes the bot's commands only work for mods and above in the guild.

        Note: The licenseinfo command will still be available.
          Disabling this command is not allowed under red's license,
          please do not look for alternative means of doing so.
        """

        if self.cache.has(ctx.guild.id):
            return await ctx.send("Mod only mode is already enabled here")

        await self.config.guild(ctx.guild).active.set(True)
        self.cache.add(ctx.guild.id)
        await ctx.tick()

    @checks.admin()
    @commands.guild_only()
    @commands.command()
    async def disablemodonlymode(self, ctx: commands.GuildContext):
        """
        Disable mod only mode in this guild.
        """

        if not self.cache.has(ctx.guild.id):
            return await ctx.send("Mod only mode is not enabled here")

        await self.config.guild(ctx.guild).active.clear()
        self.cache.remove(ctx.guild.id)
        await ctx.tick()
