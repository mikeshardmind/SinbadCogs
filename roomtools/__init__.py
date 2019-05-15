from abc import ABC
from typing import Any
from datetime import timedelta
import logging

from redbot.core import Config, commands

from .autorooms import AutoRooms
from .tempchannels import TempChannels

# red 3.0 backwards compatibility support
listener = getattr(commands.Cog, "listener", None)
if listener is None:

    def listener(name=None):
        return lambda x: x


def base_maker(*bases):
    """ This is by no means great """
    for base in bases:
        t = type(base)
        if t == type:
            continue
        yield t


class CompositeMetaClass(*(cls for cls in base_maker(commands.Cog, ABC))):
    """
    Fucking compatability layer for Red 3.0

    3.1 would just use 
        type(commands.Cog), type(ABC)
    and be done with it
    """

    pass


# No more major compatability Bullshit.


class RoomTools(AutoRooms, TempChannels, commands.Cog, metaclass=CompositeMetaClass):
    """
    Automagical user generated rooms with configuration.
    """

    __author__ = "mikeshardmind"
    __version__ = "7.1.4"
    __flavor_text__ = "Weird Edge case fix."

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

    @listener()
    async def on_voice_state_update(self, member, before, after):
        try:
            await self.on_voice_state_update_ar(member, before, after)
            await self.on_voice_state_update_tmpc(member, before, after)
        except Exception as exc:
            logging.exception("info, ", exec_info=True)

    @listener()
    async def on_resumed(self):
        await self.tmpc_cleanup(load=True)
        await self.ar_cleanup(load=True)


def setup(bot):
    cog = RoomTools(bot)
    bot.add_cog(cog)
