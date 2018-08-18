from datetime import timedelta

from redbot.core import Config

from .autorooms import AutoRooms
from .tempchannels import TempChannels


class RoomTools(AutoRooms, TempChannels):
    """
    Automagical user generated rooms with configuration.
    """

    __author__ = "mikeshardmind"
    __version__ = "7.0.1"

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

    async def on_resumed(self):
        await self.tmpc_cleanup(load=True)
        await self.ar_cleanup(load=True)


def setup(bot):
    cog = RoomTools(bot)
    bot.add_cog(cog)
    bot.add_listener(cog.on_voice_state_update_tmpc, "on_voice_state_update")
    bot.add_listener(cog.on_voice_state_update_ar, "on_voice_state_update")
