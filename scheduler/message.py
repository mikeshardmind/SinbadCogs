from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import List, Union

import discord

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


async def replacement_delete_messages(self, messages):
    message_ids = list(
        {m.id for m in messages if m.__class__.__name__ != "SchedulerMessage"}
    )

    if not message_ids:
        return

    if len(message_ids) == 1:
        await self._state.http.delete_message(self.id, message_ids[0])
        return

    if len(message_ids) > 100:
        raise discord.ClientException(
            "Can only bulk delete messages up to 100 messages"
        )

    await self._state.http.delete_messages(self.id, message_ids)


# This entire below block is such an awful hack. Don't look at it too closely.


@neuter_coroutines
class SchedulerMessage(discord.Message):
    """
    Subclassed discord message with neutered coroutines.

    Extremely butchered class for a specific use case.
    Be careful when using this in other use cases.
    """

    def __init__(
        self, *, content: str, author: discord.Member, channel: discord.TextChannel
    ) -> None:
        # auto current time
        self.id = discord.utils.time_snowflake(datetime.utcnow())
        # important properties for even being processed
        self.author = author
        self.channel = channel
        self.content = content
        self.guild = channel.guild  # type: ignore
        # this attribute being in almost everything (and needing to be) is a pain
        self._state = self.guild._state  # type: ignore
        # sane values below, fresh messages which are commands should exhibit these.
        self.call = None
        self.type = discord.MessageType.default
        self.tts = False
        self.pinned = False
        # suport for attachments somehow later maybe?
        self.attachments: List[discord.Attachment] = []
        # mentions
        self.mention_everyone = self.channel.permissions_for(
            self.author
        ).mention_everyone and bool(EVERYONE_REGEX.match(self.content))
        # pylint: disable=E1133
        # pylint improperly detects the inherited properties here as not being iterable
        # This should be fixed with typehint support added to upstream lib later
        self.mentions: List[Union[discord.User, discord.Member]] = list(
            filter(None, [self.guild.get_member(idx) for idx in self.raw_mentions])
        )
        self.channel_mentions: List[discord.TextChannel] = list(
            filter(
                None,
                [
                    self.guild.get_channel(idx)  # type: ignore
                    for idx in self.raw_channel_mentions
                ],
            )
        )
        self.role_mentions: List[discord.Role] = list(
            filter(None, [self.guild.get_role(idx) for idx in self.raw_role_mentions])
        )
