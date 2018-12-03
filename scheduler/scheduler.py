import asyncio
import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n

from .message import SchedulerMessage
from .logs import get_logger


class Scheduler:
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

        self.log = get_logger("sinbadcogs.scheduler")
        self.bg_task = bot.loop.create_task(self.bg_loop())

    async def bg_loop(self):
        pass
