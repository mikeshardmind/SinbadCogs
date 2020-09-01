import asyncio
import logging
from abc import ABCMeta
from datetime import timedelta
from typing import Optional
from uuid import getnode

from discord.ext.commands import CogMeta as DPYCogMeta
from redbot.core import Config, commands, config
from redbot.core.bot import Red

from .autorooms import AutoRooms
from .tempchannels import TempChannels

log = logging.getLogger("red.sinbadcogs.relays")

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


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
    __version__ = "340.0.2"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    antispam_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 30),
    ]

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

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


async def setup(bot):
    asyncio.create_task(maybe_send_owners(bot))
    cog = RoomTools(bot)
    bot.add_cog(cog)
    cog.init()


async def maybe_send_owners(bot: Red):
    # I have been provided multiple reasons to do it this way and not disable this completely.
    # You can thank someone reaching out and having a discussion about this and a balance
    # between not allowing issues being covered up or to be easily by passed up and not
    # stranding users with no other options in the immediate term. (the reason I didn't just fundamentally break the cogs)
    # This can still be circumvented, but that would be removing license information conveyed to end users.
    await bot.wait_until_red_ready()
    node_id = getnode()

    conf = config.Config.get_conf(
        None, identifier=node_id, cog_name=f"SinbadCogs-{node_id}"
    )

    conf.register_global(last_notify=[])

    async with conf.last_notify.get_lock():
        last_notify = await conf.last_notify()
        cur_uptime = list(bot.uptime.timetuple()[:6])
        if last_notify is None or cur_uptime > last_notify:

            await bot.send_to_owners(
                "This cog still functions, but I suggest you stop using Red and find an "
                "alternative that cares about the contributions of volunteers or pays their devs. "
                "I was removed from Red for not wanting my work misrepresented by the "
                "organization, and stating what I would do *if* that continued. "
                'For how much Red and it\'s members go after people who "take credit" '
                "for their work, they sure were quick to dismiss mine. "
                "The cog will likely recieve no further updates, nor does the license "
                "(which can be found here: <https://github.com/mikeshardmind/SinbadCogs/blob/v3/LICENSE>) "
                "permit public modifications by third parties."
                "\nThis message was provided by a cog in <https://github.com/mikeshardmind/SinbadCogs/> "
                "and an attempt will be made not to resend this message before the next bot restart."
            )
            await conf.last_notify.set(cur_uptime)
