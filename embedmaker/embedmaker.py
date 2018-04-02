import logging
from pathlib import Path
import itertools
import json

import discord
from discord.ext import commands

from redbot.core import Config, RedContext
from redbot.core.utils.chat_formatting import box, pagify
from .serializers import deserialize_embed, serialize_embed


class EmbedMaker:
    """
    Storable, recallable, embed maker
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '0.0.1a'

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )

    @commands.group(name="embed")
    async def _embed(self, ctx):
        """
        """
        pass

    @_embed.command(name="make")
    async def _make(self, ctx, name: str):
        """
        makes an embed
        """
        pass

    @_embed.command()
    async def make_adv(self, ctx, name: str, data: dict):
        """
        makes an embed from a dict
        """
        pass

    @_embed.command()
    async def make_global(self, ctx, name: str):
        """
        make a global embed
        """
        pass

    @_embed.command()
    async def make_global_adv(self, ctx, name: str, data: dict):
        """
        make a global embed from a dict
        """
        pass

    @_embed.command(name="list")
    async def _list(self, ctx):
        """
        lists the embeds here
        """
        pass

    @_embed.command(name="edit")
    async def _edit(self, ctx):
        """
        edits an embed
        """
        pass

    @_embed.command()
    async def list_global(self, ctx):
        """
        lists the global embeds
        """
        pass

    @_embed.command(name="remove")
    async def _remove(self, ctx):
        """
        removes an embed
        """
        pass

    @_embed.command()
    async def remove_global(self, ctx):
        """
        removes a global embed
        """

    @_embed.command()
    async def drop(self, ctx, name: str):
        """
        drops an embed here
        """
        pass

    @_embed.command()
    async def drop_global(self, ctx, name: str):
        """
        drop a global embed here
        """
        pass

    @_embed.command()
    async def dm(self, ctx, name: str, user: discord.Member):
        """
        DMs an embed
        """
        pass

    @_embed.command()
    async def dm_global(self, ctx, name: str, user: discord.Member):
        """
        DMs a global embed
        """
        pass
