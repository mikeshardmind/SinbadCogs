from typing import Any
from datetime import timedelta
from abc import ABC

from redbot.core import Config, commands

from .autorooms import AutoRooms
from .tempchannels import TempChannels


class Meta(type(commands.Cog), type(ABC)):
    """ mypy + d.py """

    pass


class RoomTools(AutoRooms, TempChannels, commands.Cog, metaclass=Meta):
    """
    Automagical user generated rooms with configuration.
    """

    __author__ = "mikeshardmind"
    __version__ = "8.0.0"

    antispam_intervals = [
        (timedelta(seconds=5), 3),
        (timedelta(minutes=1), 5),
        (timedelta(hours=1), 30),
    ]

    def __init__(self, bot) -> None:
        self.bot = bot
        self._antispam = {}
        self.tmpc_config = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="TempChannels",
        )
        self.tmpc_config.register_guild(active=False, category=None)
        self.tmpc_config.register_channel(is_temp=False)
        self.ar_config = Config.get_conf(
            None,
            identifier=78631113035100160,
            force_registration=True,
            cog_name="AutoRooms",
        )
        self.ar_config.register_guild(active=False, ownership=False)
        self.ar_config.register_channel(
            ownership=None, gameroom=False, autoroom=False, clone=False
        )
        self.bot.loop.create_task(self.on_resumed())

    @commands.Cog.listener()
    async def on_resumed(self):
        await self.tmpc_cleanup(load=True)
        await self.ar_cleanup(load=True)


def setup(bot):
    bot.add_cog(RoomTools(bot))
