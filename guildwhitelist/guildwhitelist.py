from __future__ import annotations

import logging

import discord
from redbot.core import Config
from redbot.core import commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify

_ = Translator("GuildWhitelist", __file__)
log = logging.getLogger("red.guildwhitelist")


@cog_i18n(_)
class GuildWhitelist(commands.Cog):
    """
    prevent the bot from joining servers who are not whitelisted
    or whose owner is not whitelisted or the owner of the bot
    """

    __version__ = "2.0.2"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(whitelist=[])

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.whitelist() as whitelist:
            if not any(
                x in whitelist for x in (guild.id, guild.owner.id)
            ) and not await self.bot.is_owner(guild.owner):
                log.info("leaving {0.id} {0.name}".format(guild))
                await guild.leave()

    @checks.is_owner()
    @commands.group(name="guildwhitelist", autohelp=True)
    async def gwl(self, ctx: commands.Context):
        """
        settings for guildwhitelisting
        """
        pass

    @gwl.command(name="add")
    async def gwl_add(self, ctx: commands.Context, *ids: int):
        """
        add one or more ids to the whitelist.
        This can be the ID or a guild, or a user.
        If the ID of a user, any guild owned by this user will be
        treated as if it were whitelisted.
        """
        if not ids:
            return await ctx.send_help()

        async with self.config.whitelist() as whitelist:
            for idx in ids:
                if idx not in whitelist:
                    whitelist.append(idx)
        await ctx.tick()

    @gwl.command(name="list")
    async def gwl_list(self, ctx: commands.Context):
        """
        list whitelisted IDs
        """
        whitelist = await self.config.whitelist()
        output = "\n".join((_("IDs in whitelist:\n"), *map(str, whitelist)))

        for page in pagify(output):
            await ctx.send(box(page))
        await ctx.tick()

    @gwl.command(name="remove")
    async def gwl_remove(self, ctx: commands.Context, *ids: int):
        """
        remove one or more ids from the whitelist
        """
        if not ids:
            return await ctx.send_help()

        async with self.config.whitelist() as whitelist:
            for idx in ids:
                if idx in whitelist:
                    whitelist.remove(idx)
        await ctx.tick()
