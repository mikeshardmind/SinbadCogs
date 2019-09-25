import discord
from redbot.core import commands, checks
from redbot.core.config import Config

try:
    from redbot.core.commands import RESERVED_COMMAND_NAMES
except ImportError:
    RESERVED_COMMAND_NAMES = tuple()


class AliasRewrite(commands.Cog, name="Alias"):
    """ Working on a rewrite of Alias, don't mind me...."""

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.init_custom("ALIASES", 2)
        self.config.register_custom("ALIASES")
