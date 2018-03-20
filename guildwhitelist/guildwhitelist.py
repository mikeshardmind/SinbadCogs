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

_ = CogI18n("GuildWhitelist", __file__)

log = logging.getLogger('red.guildwhitelist')

GWL_LIST_HEADER = _("IDs in whitelist\n")
FILE_NOT_FOUND = _("That doesn't appear to be a valid path for that")
FMT_ERROR = _("That file didn't appear to be a valid settings file")

DC_UNAVAILABLE = _("Data conversion is not available in your install.")


class GuildWhitelist:
    """
    prevent the bot from joining servers who are not whitelisted
    or whose owner is not whitelisted or the owner of the bot
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '1.0.0a'

    default_globals = {
        'whitelist': []
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
        async with self.config.whitelist() as whitelist:
            if not any(
                x in whitelist
                for x in (guild.id, guild.owner.id)
            ) and (
                guild.owner.id !=
                (await self.bot.application_info()).owner
            ):
                log.info('leaving {0.id} {0.name}'.format(guild))
                await guild.leave()

    @commands.group(name="guildwhitelist")
    async def gwl(self, ctx: RedContext):
        """
        settings for guildwhitelisting
        """
        if ctx.invoked_cubcommand is None:
            await ctx.send_help()

    @gwl.command(name='debuginfo', hidden=True)
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

    @gwl.command(name="add")
    async def gwl_add(self, ctx: RedContext, *ids: int):
        """
        add one or more ids to the whitelist.
        This can be the ID or a guild, or a user.
        If the ID of a user, any guild owned by this user will be
        treated as if it were whitelisted.
        """
        _ids = set(ids)
        if len(_ids) == 0:
            return await ctx.send_help()

        wl = await self.config.whitelist()
        wl = wl + _ids
        await self.config.whitelist.set(list(wl))
        await ctx.tick()

    @gwl.command(name="list")
    async def gwl_list(self, ctx: RedContext):
        """
        list whitelisted IDs
        """
        output = GWL_LIST_HEADER
        whitelist = await self.config.whitelist()

        output += "\n".join(str(x) for x in whitelist)

        for page in pagify(output):
            await ctx.send(box(pagify))
        await ctx.tick()

    @gwl.command(name="remove")
    async def gwl_remove(self, ctx: RedContext, *ids: int):
        """
        remove one or more ids from the whitelist
        """
        _ids = set(ids)
        if len(_ids) == 0:
            return await ctx.send_help()

        wl = set(await self.config.whitelist())
        wl = wl - ids
        await self.config.whitelist.set(list(wl))
        await ctx.tick()

    @gwl.command(name='import', disabled=True)
    async def gwl_import(self, ctx: RedContext, path: str):
        """
        pass the full path of the v2 settings.json
        for this cog
        """
        if not DC_AVAILABLE:
            return await ctx.send(DC_UNAVAILABLE)

        v2_data = Path(path) / 'data' / 'serverwhitelist' / 'list.json'
        if not v2_data.is_file():
            return await ctx.send(FILE_NOT_FOUND)

        existing_ids = await self.config.whitelist()

        def converter(data):
            return [int(x) for x in data.keys()]

        try:
            imported_items = converter(dc.json_load(path))
            to_set = list(set(imported_items + existing_ids))
            await self.config.whitelist.set(to_set)
        except FileNotFoundError:
            return await ctx.send(FILE_NOT_FOUND)
        except (ValueError, AttributeError, TypeError):
            return await ctx.send(FMT_ERROR)
        else:
            await ctx.tick()
