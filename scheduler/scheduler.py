import asyncio
import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n

from .message import SchedulerMessage
from .logs import get_logger

# This needs rewriting before I continue with what's here to properly support an eventual API
# from .tasks import Task

_ = Translator("And I think it's gonna be a long long time...", __file__)


@cog_i18n(_)
class Scheduler(commands.Cog):
    """
    A somewhat sane scheduler cog
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind(Sinbad)"
    __flavor_text__ = "This is mediocre first effort, to be improved."
    # pending actually allowing it to be loaded by adding a setup once ready

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(tasks={})  # Serialized Tasks go in here.
        self.log = get_logger("sinbadcogs.scheduler")
        self.bg_loop_task = bot.loop.create_task(self.bg_loop())
        self.scheduled_things = {}

    def __unload(self):
        self.bg_loop_task.cancel()
        [task.cancel() for task in self.scheduled_things.values()]

    # This never should be needed, 
    # but it doesn't hurt to add and could cover a weird edge case.
    __del__ = __unload

    async def bg_loop(self):
        while self == self.bot.get_cog("Scheduler"):
            sleep_for = await self.schedule_upcoming()
            await asyncio.sleep(sleep_for)

    async def schedule_upcoming(self) -> int:
        """
        Schedules some upcoming things as tasks. 
        
        Returns a logical amount of time to sleep for.
        """
        pass  # stuff here was removed since the rewrite of .tasks.Task 
        # needs to happen changing this portion fundamentally