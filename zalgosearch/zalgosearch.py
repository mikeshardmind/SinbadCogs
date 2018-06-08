import discord
from redbot.core import commands, checks, data_manager
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify
import asyncio
from multiprocessing import Pool
import itertools
import pathlib
import os
import unicodedata


class ZalgoSearch:
    """
    He does not come.
    """

    __author__ = "mikeshardmind"
    __version__ = "0.0.1a"

    def __init__(self, bot):
        self.bot = bot
 # TODO       
 #       self.config = Config.get_conf(
 #           self, identifier=78631113035100160, force_registration=True
 #       )
 #       self.config.register_guild(auto_enforce=1.1)
        self.pool = Pool(5)
        self._searches = {}
        self.path = data_manager.cog_data_path(self)
        self.__internal_cleanup()

    def __internal_cleanup(self):
        for f in self.path.glob("*.txt"):
            try:
                f.unlink()
            except Exception:
                pass

    def __unload(self):
        self.pool.close()
        self.__internal_cleanup()
# TODO
#    async def on_member_join(self, member):
#        pass
#
#    async def on_member_update(self, before, after):
#        pass

    @commands.guild_only()
    @checks.admin_or_permissions(administrator=True)
    @commands.command()
    async def zalgosearch(self, ctx, threshold: float=0.6, here: bool = False):
        """
        search for zalgo infringing names
        """
        if ctx.invoked_subcommand is not None:
            return
        if ctx.guild.id in self._searches:
            return await ctx.send("Search already in progress")
        to_check = [(ctx, m, threshold) for m in ctx.guild.members]
        chunksize = len(to_check) / 20
        self._searches[ctx.guild.id] = []
        self.pool.map_async(
            self.is_zalgo_map,
            to_check,
            chunksize=chunksize,
            callback=self.zalgo_map_callback,
        )
        while len(self._searches[ctx.guild.id]) != len(to_check):
            await asyncio.sleep(10)

        if here:
            to_report = filter(self._searches[ctx.guild.id])
            out = "\n".join(
                ' '.join(m.mention for m in group)
                for group in self.groups_of_n(3, to_report)
            )
            for page in pagify(out):
                await ctx.send(out)
            else:
                return

        path = self.path / f"{ctx.message.id}-zalgo.txt"
        self.path.mkdir(exist_ok=True, parents=True)
        with path.open(mode='w') as f:
            to_report = filter(self._searches[ctx.guild.id])
            for group in self.groups_of_n(3, to_report):
                out = ' '.join(m.mention for m in group)
                f.write(f"{out}\n")

        if os.path.getsize(path) < (8 * 1024 * 1024):
            with path.open(mode='rb') as f:
                try:
                    await ctx.send(file=discord.File(f))
                except discord.Forbidden:
                    error = True
                else:
                    error = False
        else:
            error = True
        if error:
            try:
                await ctx.send(
                    f"File at ```{path}``` could not be sent "
                    f"and will be deleted on unload."
                )
            except Exception:
                pass
        self._searches.pop(ctx.guild.id, None)

    def is_zalgo(self, member: discord.Member, threshold: float):
        ZALGO = ['Mn', 'Me']
        if len(member.display_name) == 0:
            return False
        threshold = len(member.display_name) * float(t)
        count = 0
        for c in member.display_name:
            if (unicodedata.category(c) in ZALGO):
                count += 1
                if count > threshold:
                    return True
        return False

    def is_zalgo_map(self, arg_tup):
        """
        This is setup for map_async
        """
        ctx, member, t = arg_tup
        ZALGO = ['Mn', 'Me']
        if len(member.display_name) == 0:
            return False
        threshold = len(member.display_name) * float(t)
        count = 0
        for c in member.display_name:
            if (unicodedata.category(c) in ZALGO):
                count += 1
                if count > threshold:
                    return (ctx, member)
        return (ctx, None)

    def zalgo_map_callback(self, out_tup):
        """
        just a callback
        """
        ctx, val = out_tup
        self._searches[ctx.guild.id].append(val)

    def groups_of_n(n, iterable):
        """
        mostly memory safe handler for grouping by n
        """
        args = [iter(iterable)] * n
        for group in itertools.zip_longest(*args):
            yield [element for element in group if element is not None]
