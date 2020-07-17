import asyncio
import logging
from abc import ABCMeta
from datetime import timedelta
from typing import Optional

from discord.ext.commands import CogMeta as DPYCogMeta
from redbot.core import Config, commands

from .autorooms import AutoRooms
from .tempchannels import TempChannels

log = logging.getLogger("red.sinbadcogs.relays")


# This previously used ``(type(commands.Cog), type(ABC))``
# This was changed to be explicit so that mypy would be slightly happier about it.
# This does introduce a potential place this can break in the future, but this would be an
# Upstream breaking change announced in advance
class CompositeMetaClass(DPYCogMeta, ABCMeta):
    """
    Wanting this to work with mypy requires a little extra care around composite classes.
    """

    pass


class RoomTools(AutoRooms, TempChannels, commands.Cog, metaclass=CompositeMetaClass):
    """
    Automagical user generated rooms with configuration.
    """

    __author__ = "mikeshardmind"
    __version__ = "339.1.0"
    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    antispam_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 30),
    ]

    def __init__(self, bot, *args) -> None:
        super().__init__(*args)
        self.bot = bot
        self._antispam = {}
        self.tmpc_config = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="TempChannels",
        )
        self.tmpc_config.register_guild(active=False, category=None, current=False)
        self.tmpc_config.register_channel(is_temp=False)
        self.ar_config = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="AutoRooms",
        )
        self.ar_config.register_guild(active=False, ownership=False)
        self.ar_config.register_channel(
            ownership=None,
            gameroom=False,
            autoroom=False,
            clone=False,
            creatorname=False,
        )
        self._ready_event = asyncio.Event()
        self._init_task: Optional[asyncio.Task] = None

    def init(self):
        self._init_task = asyncio.create_task(self.initialize())

        def done_callback(fut: asyncio.Future):

            try:
                fut.exception()
            except asyncio.CancelledError:
                log.info("roomtools didn't set up and was cancelled")
            except asyncio.InvalidStateError as exc:
                log.exception(
                    "We somehow have a done callback when not done?", exc_info=exc
                )
            except Exception as exc:
                log.exception("Unexpected exception in roomtools: ", exc_info=exc)

        self._init_task.add_done_callback(done_callback)

    async def cog_before_invoke(self, ctx):
        await self._ready_event.wait()

    async def initialize(self):
        await self.bot.wait_until_ready()
        await self.resume_or_start_handler()
        self._ready_event.set()

    def cog_unload(self):
        if self._init_task:
            self._init_task.cancel()

    @commands.Cog.listener("on_resumed")
    async def resume_or_start_handler(self):
        for guild in self.bot.guilds:
            await self.tmpc_cleanup(guild)
            await self.ar_cleanup(guild)


def setup(bot):
    cog = RoomTools(bot)
    bot.add_cog(cog)
    cog.init()
