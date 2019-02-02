import discord
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import Optional, Union, cast

from .message import SchedulerMessage


@dataclass()
class Task:
    nicename: str
    uid: Union[int, str]
    author: discord.Member
    content: str
    channel: discord.TextChannel
    initial: datetime
    recur: Optional[timedelta] = None

    def __post_init__(self):
        # I'll take the minor performance hit for the convienice of not forgetting this
        # interacts with config later.
        self.uid = str(self.uid)

    def __hash__(self):
        return hash(self.uid)

    async def get_message(self, bot):

        pfx = (await bot.get_prefix(self.channel))[0]
        content = f"{pfx}{self.content}"
        return SchedulerMessage(
            content=content, author=self.author, channel=self.channel
        )

    def to_config(self):

        return {
            self.uid: {
                "nicename": self.nicename,
                "author": self.author.id,
                "content": self.content,
                "channel": self.channel.id,
                "initial": self.initial.timestamp(),
                "recur": self.recur.total_seconds() if self.recur else None,
            }
        }

    @classmethod
    def bulk_from_config(cls, bot: discord.Client, **entries):

        for uid, data in entries.items():
            cid = data.pop("channel", 0)
            aid = data.pop("author", 0)
            initial_ts = data.pop("initial", 0)
            initial = datetime.fromtimestamp(initial_ts, tz=timezone.utc)
            recur_raw = data.pop("recur", None)
            recur = timedelta(seconds=recur_raw) if recur_raw else None
            channel = bot.get_channel(cid)
            if channel:
                author = channel.guild.get_member(aid)
                if author:
                    yield cls(
                        initial=initial,
                        recur=recur,
                        channel=channel,
                        author=author,
                        uid=uid,
                        **data,
                    )

    @property
    def next_call_delay(self) -> float:

        now = datetime.now(timezone.utc)

        if self.recur and now < self.initial:

            raw_interval = self.recur.total_seconds()

            return raw_interval - ((now - self.initial).total_seconds() % raw_interval)

        return (self.initial - now).total_seconds()
