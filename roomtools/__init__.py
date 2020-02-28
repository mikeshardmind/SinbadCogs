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

    This cog is no longer supported.
    Details as to why are available at source.
    As of time of marked unsupported,
    the cog was functional and not expected to be fragile to changes.

    With that said, it may break in the future related to discord's stated
    plans for intents changes
    due to the cog using user activity to name temporary channels.
    """

    __author__ = "mikeshardmind"
    __version__ = "330.0.2"

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


async def maybe_notify(bot):
    """
    I've done this to only notify once,
    and ensure a balance between proper
    user choice and not being a nuisance with it.

    Should 26 follow up with an attempt to prevent this based
    on what I have in my DMs, I'll just remove the check entirely instead
    as I would then value users over the project sanity given
    obvious attempts to hide issues after failing to address them.
    """
    await bot.wait_until_red_ready()
    conf = Config.get_conf(
        None,
        identifier=78631113035100160,
        force_registration=True,
        cog_name="SinbadCogs",
    )
    conf.register_global(has_notified=False)

    async with conf.has_notified.get_lock():
        if await conf.has_notified():
            return
        message = (
            "Hi, Sinbad here."
            "\nI'm glad you've found my cogs useful, and I hope they remain to be so."
            "\nGiven the reliance some servers have on their functionality, "
            "I'd like to ensure users are aware they are no longer supported by me. "
            "I would suggest you find another solution prior to these breaking, "
            "even if that only entails forking the repository to manage any needed "
            "changes yourself. **I do not anticipate these to break any time soon** "
            "but servers which rely on the functionality within should understand "
            "that the author is no longer involved in maintaining those functionalities."
            "\nMy reasons for this are documented here: "
            "<https://github.com/mikeshardmind/SinbadCogs/blob/v3/why_no_support.md> "
            "\n\nI will not reconsider. I would appreicate if people kept any statements "
            "related to this constructive in nature. While I have left due to this, "
            "it is not beyond possibility that people and the state of things improve. "
            "This information is only provided for making an informed decision, and I "
            "do not condone using it for purposes other than this and improvement "
            "by involved parties."
        )

        await bot.send_to_owners(message)
        await conf.has_notified.set(True)


def setup(bot):
    cog = RoomTools(bot)
    bot.add_cog(cog)
    cog.init()
    asyncio.create_task(maybe_notify(bot))
