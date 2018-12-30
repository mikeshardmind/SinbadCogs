import io
import subprocess
import functools
from concurrent.futures import ThreadPoolExecutor

import discord
from redbot.core import commands, checks


class Runner(commands.Cog):
    """
    Look, it works..... don't use this.
    """

    def __init__(self, bot):
        self.bot = bot
        self.executor = ThreadPoolExecutor()

    def __unload(self):
        self.executor.shutdown(wait=False)

    async def _run(self, command):

        return (
            await self.bot.loop.run_in_executor(
                self.executor,
                functools.partial(
                    subprocess.run,
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                ),
            )
        ).stdout

    @checks.is_owner()
    @commands.command(hidden=True)
    async def shell(self, ctx, *, command):
        """
        runs a command
        """
        async with ctx.typing():
            result = await self._run(command)
            fp = io.BytesIO(result)
            fp.seek(0)
        await ctx.send(files=[discord.File(fp, filename=f"{ctx.message.id}.log")])

    @checks.is_owner()
    @commands.command(hidden=True)
    async def killshells(self, ctx):
        """
        kills the shells
        """
        self.executor.shutdown(wait=False)
        self.executor = ThreadPoolExecutor()
        await ctx.tick()
