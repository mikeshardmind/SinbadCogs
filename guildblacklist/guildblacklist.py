import logging

import discord
from discord.ext import commands

from redbot.core.i18n import CogI18n
from redbot.core import Config, RedContext
from redbot.core.utils.chat_formatting import box, pagify
from .dataconverter import DataConverter

_ = CogI18n("GuildBlacklist", __file__)

log = logging.getLogger('red.guildblacklist')

GBL_LIST_HEADER = _("IDs in blacklist")
FILE_NOT_FOUND = _("That doesn't appear to be a valid path for that")
FMT_ERROR = _("That file didn't appear to be a valid settings file")


class GuildBlacklist:
    """
    prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '0.0.1a'
    v2converter = {
        'blacklist': lambda v2: set(int(i) for i in v2.keys())
    }

    default_globals = {
        'blacklist': set()
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_global(**self.default_globals)
        self.dc = DataConverter(self.config)

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
            blacklist.update(_ids)
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

        bl = await self.config.blacklist()
        bl = bl - _ids
        await self.config.blacklist.set(bl)
        await ctx.tick()

    @gbl.command(name='import')
    async def gbl_import(self, ctx: RedContext, path: str):
        """
        pass the full path of the v2 settings.json
        for this cog
        """
        try:
            await self.dc.convert(path, self.v2converter)
        except FileNotFoundError:
            return await ctx.send(FILE_NOT_FOUND)
        except ValueError:
            return await ctx.send(FMT_ERROR)
        except RuntimeError as e:
            log.exception("Data conversion failure")
        else:
            await ctx.tick()
