from datetime import datetime
import logging
import discord
from redbot.core import commands
import asyncio
from collections.abc import Awaitable


class DummyAwaitable(Awaitable):
    def __await__(self):
        yield


def neuter_coroutines(klass):
    # I might forget to modify this with discord.py updates, so lets automate it.

    for attr in dir(klass):
        _ = getattr(klass, attr, None)
        if asyncio.iscoroutinefunction(_):

            def dummy(self):
                return DummyAwaitable()

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
        # Stuff below is book keeping.
        self.call = None
        self.mentions = []
        self.role_mentions = []
        self.channel_mentions = []
        self.type = discord.MessageType(0)
        self.tts = False
