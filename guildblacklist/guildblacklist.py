import logging
from pathlib import Path
import itertools

import discord

from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core import Config
from redbot.core import __version__ as redversion
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.data_converter import DataConverter as dc

_ = Translator("GuildBlacklist", __file__)

log = logging.getLogger("red.guildblacklist")

GBL_LIST_HEADER = _("IDs in blacklist")
FILE_NOT_FOUND = _("That doesn't appear to be a valid path for that")
FMT_ERROR = _("That file didn't appear to be a valid settings file")


@cog_i18n(_)
class GuildBlacklist:
    """
    prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "1.0.1a"

    default_globals = {"blacklist": []}

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(**self.default_globals)

    async def __local_check(self, ctx: commands.Context):
        return await ctx.bot.is_owner(ctx.author)

    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.blacklist() as blacklist:
            if any(x in blacklist for x in (guild.id, guild.owner.id)):
                log.info("leaving {0.id} {0.name}".format(guild))
                await guild.leave()

    @commands.group(name="guildblacklist", autohelp=True)
    async def gbl(self, ctx: commands.Context):
        """
        settings for guildblacklisting
        """
        pass

    @gbl.command(name="debuginfo", hidden=True)
    async def dbg_info(self, ctx: commands.Context):
        """
        debug info
        """
        ret = (
            "Author: {}".format(self.__author__)
            + "\nVersion: {}".format(self.__version__)
            + "\nd.py Version {}.{}.{}".format(*discord.version_info)
            + "\nred version {}".format(redversion)
        )
        await ctx.send(box(ret))

    @gbl.command(name="add")
    async def gbl_add(self, ctx: commands.Context, *ids: int):
        """
        add one or more ids to the blacklist.
        This can be the ID or a guild, or a user.
        If the ID of a user, any guild owned by this user will be
        treated as if it were blacklisted.
        """
        if len(ids) == 0:
            return await ctx.send_help()

        blacklist = await self.config.blacklist()
        blacklist = blacklist + list(ids)
        to_set = unique(blacklist)
        await self.config.blacklist.set(to_set)
        await ctx.tick()

    @gbl.command(name="list")
    async def gbl_list(self, ctx: commands.Context):
        """
        list blacklisted IDs
        """
        output = GBL_LIST_HEADER
        blacklist = await self.config.blacklist()
        output += "\n".join(str(x) for x in blacklist)

        for page in pagify(output):
            await ctx.send(box(page))
        await ctx.tick()

    @gbl.command(name="remove")
    async def gbl_remove(self, ctx: commands.Context, *ids: int):
        """
        remove one or more ids from the blacklist
        """
        if len(ids) == 0:
            return await ctx.send_help()

        bl = await self.config.blacklist()
        bl = [x for x in bl if x not in ids]
        await self.config.blacklist.set(bl)
        await ctx.tick()

    @gbl.command(name="import", disabled=True)
    async def gbl_import(self, ctx: commands.Context, path: str):
        """
        pass the full path of the v2 settings.json
        for this cog
        """

        v2_data = Path(path) / "data" / "serverblacklist" / "list.json"
        if not v2_data.is_file():
            return await ctx.send(FILE_NOT_FOUND)

        existing_ids = await self.config.blacklist()

        def converter(data):
            return [int(x) for x in data.keys()]

        try:
            imported_items = converter(dc.json_load(path))
            to_set = list(set(imported_items + existing_ids))
            await self.config.blacklist.set(to_set)
        except FileNotFoundError:
            return await ctx.send(FILE_NOT_FOUND)
        except (ValueError, AttributeError, TypeError):
            return await ctx.send(FMT_ERROR)
        else:
            await ctx.tick()


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]
