import io
import subprocess

import discord
from redbot.core import commands, checks


class Runner(commands.Cog):
    """
    Look, it works..... don't use this.
    """

    @checks.is_owner()
    @commands.command(hidden=True)
    async def shell(self, ctx, *, command):
        """
        runs a command
        """
        data = subprocess.check_output(
            f"{command}; exit 0", stderr=subprocess.STDOUT, shell=True
        )
        fp = io.BytesIO(data)
        fp.seek(0)
        await ctx.send(files=[discord.File(fp, filename=f"{ctx.message.id}.log")])
