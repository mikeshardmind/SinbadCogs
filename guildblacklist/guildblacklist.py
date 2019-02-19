import logging
import discord

from redbot.core import commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core import Config
from redbot.core import __version__ as redversion
from redbot.core.utils.chat_formatting import box, pagify

log = logging.getLogger("red.guildblacklist")

T_ = Translator("GuildBlacklist", __file__)
_ = lambda s: s

GBL_LIST_HEADER = _("IDs in blacklist:\n")
FILE_NOT_FOUND = _("That doesn't appear to be a valid path for that")

_ = T_


@cog_i18n(_)
class GuildBlacklist(commands.Cog):
    """
    prevent the bot from joining servers by either
    the server's ID, or the serverowner's ID
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.0.5"
    __flavor_text__ = "Post launch cleanup."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(blacklist=[])

    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.blacklist() as blacklist:
            if any(x in blacklist for x in (guild.id, guild.owner.id)):
                log.info("leaving {0.id} {0.name}".format(guild))
                await guild.leave()

    @checks.is_owner()
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

        async with self.config.blacklist() as blacklist:
            for idx in ids:
                if idx in blacklist:
                    blacklist.remove(idx)
        await ctx.tick()
