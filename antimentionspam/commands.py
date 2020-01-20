from typing import TYPE_CHECKING as TYPE_CHECKING
import discord as _discord

from discord.ext.commands import guild_only
from redbot.core.commands.commands import command, Cog, group
from redbot.core.commands.context import Context

#  Remove after resolution of GH: Cog-Creators/Red-DiscordBot#3407

if TYPE_CHECKING:

    class GuildContext(Context):
        @property
        def author(self) -> _discord.Member:
            ...

        @property
        def channel(self) -> _discord.TextChannel:
            ...

        @property
        def guild(self) -> _discord.Guild:
            ...


else:
    GuildContext = Context
