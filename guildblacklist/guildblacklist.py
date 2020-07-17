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


class GuildBlacklist(commands.Cog):
    """
    Prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID
    """

    __version__ = "339.1.0"

    __end_user_data_statement__ = (
        "This cog persistently stores the minimum "
        "amount of data needed to maintain a server and server owner blacklist. "
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
            async with self.config.blacklist() as blist:
                if user_id in blist:
                    blist.remove(user_id)
        elif requester == "owner":
            await self.bot.send_to_owners(
                "`GuildBlacklist` recieved a data deletion request "
                f"from a bot owner for ID : `{user_id}`."
                "\nThis cog will remove the ID if you use the command "
                "to unblacklist them, but is retaining the "
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
        output = "\n".join(("IDs in blacklist:\n", *map(str, blacklist)))

        page_gen = cast(Generator[str, None, None], pagify(output))

        try:
            for page in page_gen:
                await ctx.send(box(page))
        finally:
            page_gen.close()
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

    @gbl.command(name="movesettings")
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

        blocked_ids = await self.config.blacklist()

        for idx in blocked_ids:
            await nc.guild_from_id(idx).blocked.set(True)
            await nc.user_from_id(idx).blocked.set(True)
