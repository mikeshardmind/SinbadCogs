import discord
from redbot.core import commands, checks, data_manager
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify
import asyncio
from multiprocessing import Pool
import pathlib
import os

from .utils import is_zalgo_map, groups_of_n, zalgo_callback


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
        self.path = data_manager.cog_data_path(self)
        self.__internal_cleanup()
        self.pool = Pool(5)
        self.searches = {}

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
    async def zalgosearch(self, ctx, threshold: float=0.6):
        """
        search for zalgo infringing names
        """
        if ctx.invoked_subcommand is not None:
            return
        if ctx.guild.id in self.searches:
            return await ctx.send("Search already in progress")
        self.path.mkdir(exist_ok=True, parents=True)
        
        to_check = [(ctx, m, threshold) for m in ctx.guild.members]
        chunksize = max(len(to_check) / 20, 1)
        self.searches[ctx.guild.id] = []
        
        multiresults = [
            self.pool.apply_async(is_zalgo_map, args) for args in to_check
        ]

        while not all(result.ready() for result in multiresults):
            await asyncio.sleep(10)
        else:
            finished = [z.get() for z in multiresults]

        path = self.path / f"{ctx.message.id}-zalgo.txt"
        with path.open(mode='w') as f:
            members = filter(finished)
            for group in groups_of_n(3, members):
                f.write(' '.join(m.mention for m in group) + '\n')

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
        self.searches.pop(ctx.guild.id, None)

