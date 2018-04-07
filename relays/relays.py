import asyncio
import discord
from discord.ext import commands

from redbot.core.utils.chat_formatting import box, pagify
from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.i18n import CogI18n
from redbot.core.utils.mod import mass_purge, slow_deletion

from .relay import NwayRelay, OnewayRelay
from .helpers import unique, embed_from_msg, txt_channel_finder

_ = CogI18n("Relays", __file__)

NAME_EXISTS = _("A relay of that name already exists.")

MOAR_CHANNELS = _("You didn't give me enough channels.")

UNFOUND = _("I could not find a channel for the following inputs\n")

MULTIFOUND = _("The following inputs could not be matched safely, "
               "please try again using their ID or mention\n")

NO_LOOPING = _("I won't set up a relay which would "
               "have a channel send to itself.")

NO_SUCH_RELAY = _("No relay by that name")

INTERACTIVE_PROMPT_HEADER = _("Please select a relay by number, "
                              "or '-1' to quit")

INVALID_CHOICE = _("That wasn't a valid choice")

TIMEOUT = _("You took too long, try again later.")

ONE_WAY_OUTPUT_TEMPLATE = [
    _("Relay type: one way"),
    _("Source:"),
    _("Destination:"),
    _("Destinations:")
]

NWAY_OUTPUT_TEMPLATE = [
    _("Relay type: multiway"),
    _("Channels: ")
]


class Relays:
    """
    Provides channel relays
    """

    __author__ = 'mikeshardmind(Sinbad#0001)'
    __version__ = '1.0.0b'

    def __init__(self, bot: Red):
        self. bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_global(one_ways={}, nways={})
        self.bot.loop.create_task(self.initialize())

    async def __before_invoke(self, ctx):
        while not hasattr(self, 'oneways'):
            asyncio.sleep(2)

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

    async def write_data(self):
        nway_data = {
            k: v.to_data() for k, v in self.nways.items()
        }
        oneway_data = {
            k: v.to_data() for k, v in self.oneways.items()
        }
        await self.config.one_ways.set(oneway_data)
        await self.config.nways.set(nway_data)

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
        while not hasattr(self, 'oneways'):
            asyncio.sleep(2)
        for dest in self.gather_destinations(message):
            await dest.send(
                embed=embed_from_msg(message)
            )

    def validate_inputs(self, *chaninfo: str):
        ret = {}
        for info in chaninfo:
            x = txt_channel_finder(self.bot, info)
            if len(x) == 1:
                val = x[0]
            elif len(x) == 0:
                val = None
            else:
                val = False
            ret[info] = val
        return ret

    async def validation_error(self, ctx: RedContext, validation: dict):
        error_str = ""
        not_founds = [k for k, v in validation.items() if v is None]
        multi_match = [k for k, v in validation.items() if v is False]
        if not_founds:
            error_str += UNFOUND
            error_str += "\n".join(not_founds)
            if multi_match:
                error_str += "\n\n"
        if multi_match:
            error_str += MULTIFOUND
            error_str += "\n".join(multi_match)
        for page in pagify(error_str):
            await ctx.send(box(page))

    async def interactive_selection(self, ctx: RedContext):
        output = ""
        names = self.relay_names
        if len(names) == 0:
            return -1
        for i, name in enumerate(names, 1):
            output += "{}: {}\n".format(i, name)
        output += INTERACTIVE_PROMPT_HEADER
        msgs_to_del = []
        for page in pagify(output, delims=["\n"]):
            msgs_to_del.append(await ctx.send(box(page)))

        def pred(m):
            return m.channel == ctx.channel and m.author == ctx.author

        try:
            message = await self.bot.wait_for(
                'message', check=pred, timeout=60
            )
        except asyncio.TimeoutError:
            await ctx.send(TIMEOUT)
            ret = None
        else:
            try:
                message = int(message.content.strip())
                if message < 1:
                    if message == -1:
                        return
                    raise IndexError("We only want positive indexes")
                else:
                    name = names[message - 1]
            except (ValueError, IndexError):
                await ctx.send(INVALID_CHOICE)
                ret = None
            else:
                ret = name

        if isinstance(ctx.channel, discord.TextChannel):
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await mass_purge(msgs_to_del, ctx.channel)
                return ret

        await slow_deletion(msgs_to_del)
        return ret

    def get_relay_info(self, name: str):
        if name in self.oneways:
            relay = self.oneways[name]
            quanitity_conditional = "{template[2]}" if len(
                relay.destinations) == 1 else "{template[3]}\n"
            msg = "\n".join([
                "{template[0]}",
                "{template[1]} {source.name}",
                quanitity_conditional
            ]).format(source=relay.source, template=ONE_WAY_OUTPUT_TEMPLATE)
            msg += "\n".join([x.name for x in relay.destinations])

        if name in self.nways:
            relay = self.nways[name]
            msg = "\n".join(NWAY_OUTPUT_TEMPLATE) + "\n"
            msg += "\n".join(x.name for x in relay.channels)

        return msg

    @commands.command()
    async def makerelay(self, ctx: RedContext, name: str, *channels: str):
        """
        Makes a multiway relay
        """

        if name in self.relay_names:
            return await ctx.send(NAME_EXISTS)

        if len(channels) < 2:
            return await ctx.send(MOAR_CHANNELS)

        if len(channels) != len(unique(channels)):
            return await ctx.send(NO_LOOPING)

        validation = self.validate_inputs(*channels)
        if not all(validation.values()):
            return await self.validation_error(ctx, validation)

        self.nways[name] = NwayRelay(
            channels=list(validation.values())
        )
        await self.write_data()
        await ctx.tick()

    @commands.command()
    async def makeoneway(self, ctx: RedContext,
                         name: str, source: str, *destinations: str):
        """
        Makes a relay which forwards a channel to one or more others
        """

        if name in self.relay_names:
            return await ctx.send(NAME_EXISTS)

        if len(destinations) < 1:
            return await ctx.send(MOAR_CHANNELS)

        if source in destinations or len(
                unique(destinations)) != len(destinations):
            return await ctx.send(NO_LOOPING)

        validation = self.validate_inputs(source, *destinations)
        if not all(validation.values()):
            return await self.validation_error(ctx, validation)

        self.oneways[name] = OnewayRelay(
            source=validation.pop(source),
            destinations=list(validation.values())
        )
        await self.write_data()
        await ctx.tick()

    @commands.command()
    async def relayinfo(self, ctx: RedContext, name: str=None):
        """
        gets info about relays

        if used without a name, is interactive
        """

        if name is None:
            name = await self.interactive_selection(ctx)
            if name is None:
                return

        if name not in self.relay_names:
            return await ctx.send(NO_SUCH_RELAY)

        msg = self.get_relay_info(name)
        for page in pagify(msg):
            await ctx.send(box(page))

    @commands.command()
    async def rmrelay(self, ctx: RedContext, name: str=None):
        """
        removes a relay

        if a name is not provided, is interactive
        """

        if name is None:
            name = await self.interactive_selection(ctx)
            if name is None:
                return

        if name not in self.relay_names:
            return await ctx.send(NO_SUCH_RELAY)

        self.nways.pop(name, None)
        self.oneways.pop(name, None)
        await self.write_data()
        await ctx.tick()
