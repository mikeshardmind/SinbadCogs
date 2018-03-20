import logging
from pathlib import Path

import discord
from discord.ext import commands

from redbot.core.i18n import CogI18n
from redbot.core import Config, RedContext
from redbot.core import __version__ as redversion
from redbot.core.utils.chat_formatting import box, pagify
try:
    from redbot.core.utils.data_converter import DataConverter as dc
except ImportError:
    DC_AVAILABLE = False
else:
    DC_AVAILABLE = True

_ = CogI18n("GuildBlacklist", __file__)

log = logging.getLogger('red.guildblacklist')

GBL_LIST_HEADER = _("IDs in blacklist")
FILE_NOT_FOUND = _("That doesn't appear to be a valid path for that")
FMT_ERROR = _("That file didn't appear to be a valid settings file")

DC_UNAVAILABLE = _("Data conversion is not available in your install.")


class GuildBlacklist:
    """
    prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '0.0.1a'

    default_globals = {
        'blacklist': []
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_global(**self.default_globals)

    async def __local_check(self, ctx: RedContext):
        return await ctx.bot.is_owner(ctx.author)

    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.blacklist() as blacklist:
            if any(
                x in blacklist
                for x in (guild.id, guild.owner.id)
            ):
                log.info('leaving {0.id} {0.name}'.format(guild))
                await guild.leave()

    @commands.group(name="guildblacklist")
    async def gbl(self, ctx: RedContext):
        """
        settings for guildblacklisting
        """
        if ctx.invoked_cubcommand is None:
            await ctx.send_help()

    @gbl.command(name='debuginfo', hidden=True)
    async def dbg_info(self, ctx: RedContext):
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
    async def gbl_add(self, ctx: RedContext, *ids: int):
        """
        add one or more ids to the blacklist.
        This can be the ID or a guild, or a user.
        If the ID of a user, any guild owned by this user will be
        treated as if it were blacklisted.
        """
        _ids = set(ids)
        if len(_ids) == 0:
            return await ctx.send_help()

        async with self.config.blacklist() as blacklist:
            blacklist.update(list(_ids))
        await ctx.tick()

    @gbl.command(name="list")
    async def gbl_list(self, ctx: RedContext):
        """
        list blacklisted IDs
        """
        output = GBL_LIST_HEADER
        async with self.config.blacklist() as blacklist:
            for _id in blacklist:
                output += "\n{}".format(_id)

        for page in pagify(output):
            await ctx.send(box(pagify))
        await ctx.tick()

    @gbl.command(name="remove")
    async def gbl_remove(self, ctx: RedContext, *ids: int):
        """
        remove one or more ids from the blacklist
        """
        _ids = set(ids)
        if len(_ids) == 0:
            return await ctx.send_help()

        bl = set(await self.config.blacklist())
        bl = bl - ids
        await self.config.blacklist.set(list(bl))
        await ctx.tick()

    @gbl.command(name='import', disabled=True)
    async def gbl_import(self, ctx: RedContext, path: str):
        """
        pass the full path of the v2 settings.json
        for this cog
        """
        if not DC_AVAILABLE:
            return await ctx.send(DC_UNAVAILABLE)

        v2_data = Path(path) / 'data' / 'serverblacklist' / 'list.json'
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
