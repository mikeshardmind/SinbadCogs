import asyncio
from typing import Dict, Optional, List, Union

import discord
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.mod import mass_purge, slow_deletion

from .relay import NwayRelay, OnewayRelay
from .helpers import unique, embed_from_msg, txt_channel_finder

_ = Translator("Relays", __file__)


@cog_i18n(_)
class Relays(commands.Cog):
    """
    Provides channel relays
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "2.0.3"

    def __init__(self, bot: Red, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(one_ways={}, nways={}, scrub_invites=False)
        self.nways: Dict[str, NwayRelay] = {}
        self.oneways: Dict[str, OnewayRelay] = {}
        self.scrub_invites: Optional[bool] = None
        self.loaded = False

    async def cog_before_invoke(self, _ctx):
        while not self.loaded:
            await asyncio.sleep(0.1)

    async def cog_check(self, ctx):
        return await self.bot.is_owner(ctx.author)

    async def initialize(self) -> None:
        await self.bot.wait_until_ready()
        nway_dict = await self.config.nways()
        self.nways = {k: NwayRelay(bot=self.bot, **v) for k, v in nway_dict.items()}
        onewaydict = await self.config.one_ways()
        self.oneways = {
            k: OnewayRelay(bot=self.bot, **v) for k, v in onewaydict.items()
        }
        self.scrub_invites = await self.config.scrub_invites()
        self.loaded = True

    async def write_data(self):
        nway_data = {k: v.to_data() for k, v in self.nways.items()}
        oneway_data = {k: v.to_data() for k, v in self.oneways.items()}
        await self.config.one_ways.set(oneway_data)
        await self.config.nways.set(nway_data)

    @property
    def relay_names(self) -> List[str]:
        return list(self.oneways.keys()) + list(self.nways.keys())

    @property
    def relay_objs(self) -> List[Union[NwayRelay, OnewayRelay]]:
        return list((*self.oneways.values(), *self.nways.values()))

    def gather_destinations(
        self, message: discord.Message
    ) -> List[discord.TextChannel]:
        chans: List[discord.TextChannel] = []
        for r in self.relay_objs:
            chans.extend(r.get_destinations(message))
        return unique(chans)

    async def on_message(self, message: discord.Message):
        if not self.loaded:
            await self.initialize()
        if message.author == self.bot.user:
            return
        if message.type.value != 0:
            return
        for dest in self.gather_destinations(message):
            await dest.send(
                embed=embed_from_msg(message, filter_invites=self.scrub_invites)
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

    @staticmethod
    async def validation_error(ctx: commands.Context, validation: dict):
        error_str = ""
        not_founds = [k for k, v in validation.items() if v is None]
        multi_match = [k for k, v in validation.items() if v is False]
        if not_founds:
            error_str += _("I could not find a channel for the following inputs\n")
            error_str += "\n".join(not_founds)
            if multi_match:
                error_str += "\n\n"
        if multi_match:
            error_str += _(
                "The following inputs could not be matched safely, "
                "please try again using their ID or mention\n"
            )
            error_str += "\n".join(multi_match)
        for page in pagify(error_str):
            await ctx.send(box(page))

    async def interactive_selection(self, ctx: commands.Context):
        output = ""
        names = self.relay_names
        if len(names) == 0:
            return -1
        for i, name in enumerate(names, 1):
            output += "{}: {}\n".format(i, name)
        output += _("Please select a relay by number, " "or '-1' to quit")
        msgs_to_del = []
        for page in pagify(output, delims=["\n"]):
            msgs_to_del.append(await ctx.send(box(page)))

        def pred(m):
            return m.channel == ctx.channel and m.author == ctx.author

        try:
            message = await self.bot.wait_for("message", check=pred, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(_("You took too long, try again later."))
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
                await ctx.send(_("That wasn't a valid choice"))
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
        msg: str
        if name in self.oneways:
            relay = self.oneways[name]
            msg = _(
                "Relay type: one way\n"
                "Source (Channel | Server): {source.name} | {source.guild.name}\n"
                "Destinations (Channel | Server):\n"
            ).format(source=relay.source)
            msg += "\n".join(f"{x.name} | {x.guild.name}" for x in relay.destinations)

        if name in self.nways:
            nrelay = self.nways[name]
            msg = _("Relay type: multiway\nChannels Channel | Guild):\n")
            msg += "\n".join(f"{x.name} | {x.guild.name}" for x in nrelay.channels)

        return msg

    @commands.group()
    async def relayset(self, ctx: commands.Context):
        """
        Global relay behavior settings
        """
        pass

    @relayset.command(name="scrubinvites")
    async def scrinv(self, ctx: commands.Context):
        """
        Enable removal of invite links before message forwarding
        """
        self.scrub_invites = True
        await self.config.scrub_invites.set(True)
        await ctx.tick()

    @relayset.command(name="noscrubinvites")
    async def noscrinv(self, ctx: commands.Context):
        """
        Disable removal of invite links before message forwarding
        """
        self.scrub_invites = False
        await self.config.scrub_invites.set(False)
        await ctx.tick()

    @commands.command()
    async def makerelay(self, ctx: commands.Context, name: str, *channels: str):
        """
        Makes a multiway relay
        """

        if name in self.relay_names:
            return await ctx.send(_("A relay of that name already exists."))

        if len(channels) < 2:
            return await ctx.send(_("You didn't give me enough channels."))

        if len(channels) != len(unique(channels)):
            return await ctx.send(
                _("I won't set up a relay which would have a channel send to itself.")
            )

        validation = self.validate_inputs(*channels)
        if not all(validation.values()):
            return await self.validation_error(ctx, validation)

        self.nways[name] = NwayRelay(bot=self.bot, channels=list(validation.values()))
        await self.write_data()
        await ctx.tick()

    @commands.command()
    async def makeoneway(
        self, ctx: commands.Context, name: str, source: str, *destinations: str
    ):
        """
        Makes a relay which forwards a channel to one or more others
        """

        if name in self.relay_names:
            return await ctx.send(_("A relay of that name already exists."))

        if len(destinations) < 1:
            return await ctx.send(_("You didn't give me enough channels."))

        if source in destinations or len(unique(destinations)) != len(destinations):
            return await ctx.send(
                _("I won't set up a relay which would have a channel send to itself.")
            )

        validation = self.validate_inputs(source, *destinations)
        if not all(validation.values()):
            return await self.validation_error(ctx, validation)

        self.oneways[name] = OnewayRelay(
            bot=self.bot,
            source=validation.pop(source),
            destinations=list(validation.values()),
        )
        await self.write_data()
        await ctx.tick()

    @commands.command()
    async def relayinfo(self, ctx: commands.Context, name: str = None):
        """
        gets info about relays

        if used without a name, is interactive
        """

        if name is None:
            name = await self.interactive_selection(ctx)
            if name is None:
                return

        if name not in self.relay_names:
            return await ctx.send(_("No relay by that name"))

        msg = self.get_relay_info(name)
        for page in pagify(msg):
            await ctx.send(box(page))

    @commands.command()
    async def rmrelay(self, ctx: commands.Context, name: str = None):
        """
        removes a relay

        if a name is not provided, is interactive
        """

        if name is None:
            name = await self.interactive_selection(ctx)
            if name is None:
                return

        if name not in self.relay_names:
            return await ctx.send(_("No relay by that name"))

        self.nways.pop(name, None)
        self.oneways.pop(name, None)
        await self.write_data()
        await ctx.tick()
