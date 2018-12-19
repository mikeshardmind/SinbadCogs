from typing import List, Optional
from datetime import datetime
import logging
import discord
from redbot.core import commands
import asyncio
import re

EVERYONE_REGEX = re.compile(r"@here|@everyone")

async def dummy_awaitable(*args, **kwargs):
    return


def neuter_coroutines(klass):
    # I might forget to modify this with discord.py updates, so lets automate it.

    for attr in dir(klass):
        _ = getattr(klass, attr, None)
        if asyncio.iscoroutinefunction(_):

            def dummy(self):
                return dummy_awaitable

            prop = property(fget=dummy)
            setattr(klass, attr, prop)
    return klass


@neuter_coroutines
class SchedulerMessage(discord.Message):
    """
    Subclassed discord message with neutered coroutines.

    Extremely butchered class for a specific use case.
    Be careful when using this in other use cases.
    """

    def __init__(
        self, *, content: str, author: discord.User, channel: discord.TextChannel
    ) -> None:
        self.id = discord.utils.time_snowflake(datetime.utcnow())
        self.author = author
        self.channel = channel
        self.content = content
        self.guild = channel.guild
        self.attachments: List[discord.Attachment] = []
        # mentions
        self.mention_everyone = (
            self.channel.permissions_for(self.author).mention_everyone
            and bool(EVERYONE_REGEX.match(self.content))
        )
        self.mentions: Optional[List[discord.Member]] = None
        self.role_mentions: Optional[List[discord.Role]] = None
        self.channel_mentions: Optional[List[discord.TextChannel]] = None
        self._handle_mentions()
        # Stuff below is book keeping.
        self.call = None
        self.type = discord.MessageType(0)
        self.tts = False
        self.pinned = False

    # pylint: disable=E1133
    def _handle_mentions(self):
        # Yes, I'm abusing the hell out of this.
        self.mentions = list(
            filter(None, [self.guild.get_member(idx) for idx in self.raw_mentions])
        )
        self.channel_mentions = list(
            filter(
                None, [self.guild.get_channel(idx) for idx in self.raw_channel_mentions]
            )
        )
        self.role_mentions = list(
            filter(None, [self.guild.get_role(idx) for idx in self.raw_role_mentions])
        )
