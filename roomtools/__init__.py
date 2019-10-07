from abc import ABC
from datetime import timedelta

from redbot.core import Config, commands

from cog_shared.sinbad_libs import extra_setup

from .autorooms import AutoRooms
from .tempchannels import TempChannels


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    Discord.py transforms instance methods into classes as class variables which contain
    the previous instance method, with no proper ability to reference the intended instance.
    
    Then uses a metaclass to inject the instance into copies
    of those class variables which exist inside an instance descriptor

    I wish I was kidding. I wish I had the time to do something better.
    """

    pass


class RoomTools(AutoRooms, TempChannels, commands.Cog, metaclass=CompositeMetaClass):
    """
    Automagical user generated rooms with configuration.
    """

    __author__ = "mikeshardmind"
    __version__ = "7.1.5"
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
            ownership=None, gameroom=False, autoroom=False, clone=False
        )
        self.bot.loop.create_task(self.tmpc_cleanup(load=True))
        self.bot.loop.create_task(self.ar_cleanup(load=True))


@extra_setup
def setup(bot):
    cog = RoomTools(bot)
    bot.add_cog(cog)
