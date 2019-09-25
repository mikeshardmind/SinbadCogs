import discord

from redbot.core import commands
from discord.ext.commands.core import hooked_wrapped_callback


class AliasedCommand(commands.Command):
    def __init__(self, *args, **kwargs):
        self._modified_callback = kwargs.pop("_modified_callback", None)
        self._modified_converters = kwargs.pop("_modified_converters", {})
        super().__init__(*args, **kwargs)

    def _ensure_assignment_on_copy(self, other):
        other._modified_callback = self._modified_callback
        other._modified_converters = self._modified_converters
        return super()._ensure_assignment_on_copy(other)

    @classmethod
    def from_existing_command(cls, command: commands.Command):
        pass  # TODO

    def override_converter(self, param, converter):
        """ Allows some prefilling / defaults (This creates a modifed callback)"""
        pass  # TODO
