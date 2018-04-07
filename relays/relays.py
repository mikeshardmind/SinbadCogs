import discord
from discord.ext import commands
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.i18n import CogI18n
from .relay import NwayRelay, OnewayRelay
from .helpers import unique, embed_from_msg

_ = CogI18n("Relays", __file__)

NAME_EXISTS = _("A relay of that name already exists.")


class Relays:
    """
    Provides channel relays
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '1.0.0a'

    def __init__(self, bot: Red):
        self. bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_global(one_ways={}, nways={})
        self.bot.loop.create_task(self.initialize())

    async def __local_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def initialize(self) -> None:
        nway_dict = await self.config.nways()
        self.nways = {
            k: NwayRelay.from_data(self.bot, **v)
            for k, v in nway_dict.items()
        }
        onewaydict = await self.config.one_ways()
        self.oneways = {
            k: OnewayRelay.from_data(self.bot, **v)
            for k, v in onewaydict.items()
        }

    @property
    def relay_names(self):
        return list(self.oneways.keys()) + list(self.nways.keys())

    @property
    def relay_objs(self):
        return list(self.oneways.values()) + list(self.nways.values())

    def gather_destinations(self, message: discord.Message):
        chans = []
        for r in self.relay_objs:
            chans.extend(r.get_destinations(message))
        return unique(chans)

    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        for dest in self.gather_destinations(message):
            await dest.send(
                embed=embed_from_msg(message)
            )

    @commands.command()
    async def makerelay(self, ctx: RedContext, name: str, *channels: str):
        """
        Makes a multiway relay
        """

        if name in self.relay_names:
            return await ctx.send(NAME_EXISTS)

    @commands.command()
    async def makeoneway(self, ctx: RedContext,
                         name: str, source: str, *destinations: str):
        """
        Makes a relay which forwards a channel to one or more others
        """

        if name in self.relay_names:
            return await ctx.send(NAME_EXISTS)
