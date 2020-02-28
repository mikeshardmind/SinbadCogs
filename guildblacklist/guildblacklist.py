from __future__ import annotations

import logging

import discord
from redbot.core import Config
from redbot.core import commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.data_manager import cog_data_path

_ = Translator("GuildBlacklist", __file__)


class AddOnceHandler(logging.FileHandler):
    """
    Red's hot reload logic will break my logging if I don't do this.
    """


log = logging.getLogger("red.sinbadcogs.guildblacklist")

for handler in log.handlers:
    # Red hotreload shit.... can't use isinstance, need to check not already added.
    if handler.__class__.__name__ == "AddOnceHandler":
        break
else:
    fp = cog_data_path(raw_name="GuildBlacklist") / "blacklist.log"
    handler = AddOnceHandler(fp)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="%",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


@cog_i18n(_)
class GuildBlacklist(commands.Cog):
    """
    Prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID

    This cog is no longer supported.
    Details as to why are available at source.
    As of time of marked unsupported,
    the cog was functional and not expected to be fragile to changes.
    """

    __version__ = "333.0.4"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(blacklist=[])

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.blacklist() as blacklist:
            if any(x in blacklist for x in (guild.id, guild.owner.id)):
                log.info("leaving guild: %s", guild)
                await guild.leave()

    @checks.is_owner()
    @commands.group(name="guildblacklist", autohelp=True)
    async def gbl(self, ctx: commands.Context):
        """
        settings for guildblacklisting
        """
        pass

    @gbl.command(name="add")
    async def gbl_add(self, ctx: commands.Context, *ids: int):
        """
        add one or more ids to the blacklist.
        This can be the ID or a guild, or a user.
        If the ID of a user, any guild owned by this user will be
        treated as if it were blacklisted.
        """
        if not ids:
            return await ctx.send_help()

        async with self.config.blacklist() as blacklist:
            for idx in ids:
                if idx not in blacklist:
                    blacklist.append(idx)
        await ctx.tick()

    @gbl.command(name="list")
    async def gbl_list(self, ctx: commands.Context):
        """
        list blacklisted IDs
        """
        blacklist = await self.config.blacklist()
        output = "\n".join((_("IDs in blacklist:"), *map(str, blacklist)))

        for page in pagify(output):
            await ctx.send(box(page))
        await ctx.tick()

    @gbl.command(name="remove")
    async def gbl_remove(self, ctx: commands.Context, *ids: int):
        """
        remove one or more ids from the blacklist
        """
        if not ids:
            return await ctx.send_help()

        async with self.config.blacklist() as blacklist:
            for idx in ids:
                if idx in blacklist:
                    blacklist.remove(idx)
        await ctx.tick()
