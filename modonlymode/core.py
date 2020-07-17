from collections import defaultdict
from typing import Dict, Optional

import discord
from discord.utils import SnowflakeList
from redbot.core import Config, checks, commands
from redbot.core.bot import Red


class ModOnlyMode(commands.Cog):
    """
    Cog to limit the bot to mods and higher.
    """

    __version__ = "339.1.3"
    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(
        self,
        bot: Red,
        config: Config,
        cache: SnowflakeList,
        exclusion_cache: Dict[str, SnowflakeList],
    ):
        self.bot: Red = bot
        self.cache: SnowflakeList = cache
        self.config: Config = config
        self.exclusion_cache: Dict[str, SnowflakeList] = exclusion_cache

    @classmethod
    async def setup(cls, bot: Red):
        config = Config.get_conf(None, 78631113035100160, cog_name="ModOnlyMode")
        config.register_guild(active=False, exclusions=[])

        all_guild_data = await config.all_guilds()

        cache = SnowflakeList(())
        exclusion_cache: Dict[str, SnowflakeList] = defaultdict(
            lambda: SnowflakeList(())
        )

        for guild_id, guild_data in all_guild_data.items():
            if guild_data.get("active", False):
                cache.add(guild_id)
            for exclusion in guild_data.get("exclusions", []):
                exclusion_cache[exclusion].add(guild_id)

        cog = cls(bot, config, cache, exclusion_cache)
        bot.add_cog(cog)

    async def __permissions_hook(self, ctx: commands.Context) -> Optional[bool]:
        if ctx.guild and self.cache.has(ctx.guild.id):
            assert isinstance(ctx.author, discord.Member), "mypy"  # nosec
            if not await self.bot.is_mod(ctx.author):
                if ctx.cog and self.exclusion_cache[ctx.cog.qualified_name].has(
                    ctx.guild.id
                ):
                    return None
                return False

        return None

    @checks.admin()
    @commands.guild_only()
    @commands.group(name="modonlymodeset", aliases=["momset"])
    async def momset(self, ctx: commands.Context):
        """
        Settings for ModOnlyMode
        """

    @momset.command()
    async def enable(self, ctx: commands.GuildContext):
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

    @momset.command()
    async def disable(self, ctx: commands.GuildContext):
        """
        Disable mod only mode in this guild.
        """

        if not self.cache.has(ctx.guild.id):
            return await ctx.send("Mod only mode is not enabled here")

        await self.config.guild(ctx.guild).active.clear()
        self.cache.remove(ctx.guild.id)
        await ctx.tick()

    @momset.command()
    async def excludecog(self, ctx: commands.GuildContext, *, cog_name: str):
        """
        Exclude a cog from mod only mode.
        """

        if self.bot.get_cog(cog_name) is None:
            return await ctx.send_help()

        if self.exclusion_cache[cog_name].has(ctx.guild.id):
            return await ctx.send("That cog was already excluded.")

        async with self.config.guild(ctx.guild).exclusions() as cog_list:
            cog_list.append(cog_name)
            self.exclusion_cache[cog_name].add(ctx.guild.id)
            await ctx.tick()

    @momset.command()
    async def reincludecog(self, ctx: commands.GuildContext, *, cog_name: str):
        """
        Reinclude a cog in mod only mode.
        """

        if self.bot.get_cog(cog_name) is None:
            return await ctx.send_help()

        if not self.exclusion_cache[cog_name].has(ctx.guild.id):
            return await ctx.send("That cog was not excluded.")

        async with self.config.guild(ctx.guild).exclusions() as cog_list:
            cog_list.remove(cog_name)
            self.exclusion_cache[cog_name].remove(ctx.guild.id)
            await ctx.tick()
