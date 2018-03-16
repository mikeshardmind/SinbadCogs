from redbot.core.data_manager import cog_data_path
import discord
import asyncio
from .renderer import TexRenderer


class RenderTex:
    """
    auto render tex blocks
    """

    def __init__(self, bot):
        self.dpi = 1200  # TODO: configurable
        self.datapath = str(cog_data_path(self)) + '/'

    async def on_message(self, message: discord.Message):
        if not (message.content.startswith('```tex')
                and message.content.endswith('```')):
            return
        texblock = '\n'.join(message.content.split('\n')[1:-1])
        if len(texblock) == 0:
            return

        r = TexRenderer(tex=texblock, dpi=self.dpi, datapath=self.datapath)
        r.start()

        while r.is_alive():
            await asyncio.sleep(1)

        if not r.error and r.rendered_files:
            [await message.channel.send(file=discord.File(f))
             for f in r.rendered_files]
            # I'd love to use files, but discord is reordering them
            del r
