# This probably seems like overkill
# It is for the current form, it isn't with future features in mind.
import contextlib
from datetime import datetime
from typing import List, Callable, Union, Optional, Dict, Iterator

import discord

MessagePredicate = Callable[[discord.Message], bool]


class RecentActivityRecord:

    __slots__ = ("activities", "messages")

    def __init__(self):
        self.activities: List[datetime] = []
        self.messages: List[discord.Message] = []

    def add_activity(self, when: datetime):
        self.activities.append(when)

    def add_message(self, message: discord.Message):
        self.messages.append(message)

    def __len__(self):
        return len(self.activities) + len(self.messages)

    def _filter(
        self,
        *,
        after: Optional[datetime] = None,
        message_check: Optional[MessagePredicate] = None,
    ) -> List[Union[datetime, discord.Message]]:

        ret: List[Union[datetime, discord.Message]] = []

        for a in self.activities:
            if after and a <= after:
                continue
            ret.append(a)

        for m in self.messages:
            if after and m.created_at <= after:
                continue

            if message_check and not message_check(m):
                continue

            ret.append(m)

        return ret

    def conditional_count(
        self,
        *,
        after: Optional[datetime] = None,
        message_check: Optional[MessagePredicate] = None,
    ) -> int:

        ret = len(self._filter(after=after, message_check=message_check))

        return ret

    def conditional_remove(
        self,
        *,
        before: Optional[datetime] = None,
        message_check: Optional[MessagePredicate] = None,
    ):
        if before:
            self.activities = [a for a in self.activities if a > before]

            if message_check:
                self.messages = [
                    m
                    for m in self.messages
                    if m.created_at > before and message_check(m)
                ]
            else:
                self.messages = [m for m in self.messages if m.created_at > before]

        elif message_check:
            self.messages = [m for m in self.messages if message_check(m)]


RecordDict = Dict[discord.Guild, Dict[discord.Member, RecentActivityRecord]]


class RecordHandler:

    __slots__ = ("records",)

    def __init__(self):
        self.records: RecordDict = {}

    def proccess_message(self, message):

        try:
            member = message.author
            guild = member.guild
            if not (guild and member and not member.bot):
                return
        except AttributeError:
            return

        if guild not in self.records:
            self.records[guild] = {}

        if member not in self.records[guild]:
            self.records[guild][member] = RecentActivityRecord()

        self.records[guild][member].add_message(message)

    def get_active_for_guild(
        self,
        *,
        guild: discord.Guild,
        after: datetime,
        message_check: Optional[MessagePredicate] = None,
    ) -> Iterator[discord.Member]:

        with contextlib.suppress(KeyError):
            for member, rec in self.records[guild].items():
                if rec.conditional_count(after=after, message_check=message_check):
                    yield member

    def clear_before(self, *, guild: discord.Guild, before: datetime):
        with contextlib.suppress(KeyError):
            for rec in self.records[guild].values():
                rec.conditional_remove(before=before)
