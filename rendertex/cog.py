from redbot.core import checks
from redbot.core.config import Config as RealConfig

import discord
from discord.ext import commands
import asyncio
from .renderer import TexRenderer


class RenderTex:
    """
    auto render tex blocks
    """

    def __init__(self, bot):
        self.bot = bot
        self.dpi = 600  # TODO: configurable
        self.settings = RealConfig.get_conf(
            self, 78631113035100160, force_registration=True)
        self.settings.register_guild(tex=False)

    async def on_message(self, message: discord.Message):
        if (await self.bot.is_owner(message.author)):
            pass
        elif not isinstance(message.channel, discord.TextChannel):
            return
        elif not (await self.settings.guild(message.guild).tex()):
            return
        if not (message.content.startswith('```tex')
                and message.content.endswith('```')):
            return
        texblock = '\n'.join(message.content.split('\n')[1:-1])
        if len(texblock) == 0:
            return

        r = TexRenderer(tex=texblock, dpi=self.dpi)
        r.start()

        while r.is_alive():
            await asyncio.sleep(1)

        if not r.error and r.rendered_files:
            [await message.channel.send(file=discord.File(f))
             for f in r.rendered_files]
            # I'd love to use files, but discord is reordering them
            r.cleanup()
        del r

    @commands.command()
    @checks.is_owner()
    async def toggletexhere(self, ctx):
        """
        toggles tex responses for the current server
        """

        x = not (await self.settings.guild(ctx.guild).tex())
        await self.settings.guild(ctx.guild).tex.set(x)

        resp = "LaTeX " + ("enabled" if x else "disabled")
        await ctx.send(resp)
