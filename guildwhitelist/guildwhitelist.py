from __future__ import annotations

import logging
from typing import Generator, Literal, cast

import discord
from redbot.core import Config, checks, commands
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, pagify


class AddOnceHandler(logging.FileHandler):
    """
    Red's hot reload logic will break my logging if I don't do this.
    """


log = logging.getLogger("red.sinbadcogs.guildwhitelist")


for handler in log.handlers:
    # Red hotreload shit.... can't use isinstance, need to check not already added.
    if handler.__class__.__name__ == "AddOnceHandler":
        break
else:
    fp = cog_data_path(raw_name="GuildWhitelist") / "whitelist.log"
    handler = AddOnceHandler(fp)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="%",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


class GuildWhitelist(commands.Cog):
    """
    Prevent the bot from joining servers who are not whitelisted
    or whose owner is not whitelisted or the owner of the bot
    """

    __version__ = "339.1.0"

    __end_user_data_statement__ = (
        "This cog persistently stores the minimum "
        "amount of data needed to maintain a server and server owner whitelist. "
        "It will not respect data deletion by end users, nor can end users request "
        "their data from this cog since it only stores a discord ID. "
        "Discord IDs may occasionally be logged to a file as needed for audit purposes."
    )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester == "discord":
            # user is deleted, just comply
            async with self.config.whitelist() as wlist:
                if user_id in wlist:
                    wlist.remove(user_id)
        elif requester == "owner":
            await self.bot.send_to_owners(
                "`GuildWhitelist` recieved a data deletion request "
                f"from a bot owner for ID : `{user_id}`."
                "\nThis cog will remove the ID if you use the command "
                "to unwhitelist them, but is retaining the "
                "ID for operational purposes if you do not."
            )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

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
                log.info("leaving guild: %s", guild)
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
        output = "\n".join(("IDs in whitelist:\n", *map(str, whitelist)))

        page_gen = cast(Generator[str, None, None], pagify(output))

        try:
            for page in page_gen:
                await ctx.send(box(page))
        finally:
            page_gen.close()
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

    @gwl.command(name="movesettings")
    async def movesettings(self, ctx: commands.Context, *ids: int):
        """
        Migrate the settings for this cog to the new `guildjoinrestrict` cog
        """

        nc = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="GuildJoinRestrict",
        )
        nc.register_guild(allowed=False, blocked=False)
        nc.register_user(allowed=False, blocked=False)

        allowed_ids = await self.config.whitelist()

        for idx in allowed_ids:
            await nc.guild_from_id(idx).allowed.set(True)
            await nc.user_from_id(idx).allowed.set(True)
