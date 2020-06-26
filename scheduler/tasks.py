from __future__ import annotations

import contextlib
from datetime import datetime, timedelta, timezone
from typing import Optional, cast

import attr
import discord
from redbot.core.utils.chat_formatting import humanize_timedelta

from .message import SchedulerMessage


@attr.s(auto_attribs=True, slots=True)
class Task:
    nicename: str
    uid: str
    author: discord.Member
    content: str
    channel: discord.TextChannel
    initial: datetime
    recur: Optional[timedelta] = None

    def __attrs_post_init__(self):
        if self.initial.tzinfo is None:
            self.initial = self.initial.replace(tzinfo=timezone.utc)

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

            channel = cast(Optional[discord.TextChannel], bot.get_channel(cid))
            if not channel:
                continue

            author = channel.guild.get_member(aid)
            if not author:
                continue

            with contextlib.suppress(AttributeError, ValueError):
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

        if self.recur and now >= self.initial:
            raw_interval = self.recur.total_seconds()
            return raw_interval - ((now - self.initial).total_seconds() % raw_interval)

        return (self.initial - now).total_seconds()

    def to_embed(self, index: int, page_count: int, color: discord.Color):

        now = datetime.now(timezone.utc)
        next_run_at = now + timedelta(seconds=self.next_call_delay)
        embed = discord.Embed(color=color, timestamp=next_run_at)
        embed.title = f"Now viewing {index} of {page_count} selected tasks"
        embed.add_field(name="Command", value=f"[p]{self.content}")
        embed.add_field(name="Channel", value=self.channel.mention)
        embed.add_field(name="Creator", value=self.author.mention)
        embed.add_field(name="Task ID", value=self.uid)

        try:
            fmt_date = self.initial.strftime("%A %B %-d, %Y at %-I%p %Z")
        except ValueError:  # Windows
            # This looks less natural, but I'm not doing this piecemeal to emulate.
            fmt_date = self.initial.strftime("%A %B %d, %Y at %I%p %Z")

        if self.recur:
            try:
                fmt_date = self.initial.strftime("%A %B %-d, %Y at %-I%p %Z")
            except ValueError:  # Windows
                # This looks less natural, but I'm not doing this piecemeal to emulate.
                fmt_date = self.initial.strftime("%A %B %d, %Y at %I%p %Z")

            if self.initial > now:
                description = (
                    f"{self.nicename} starts running on {fmt_date}."
                    f"\nIt repeats every {humanize_timedelta(timedelta=self.recur)}"
                )
            else:
                description = (
                    f"{self.nicename} started running on {fmt_date}."
                    f"\nIt repeats every {humanize_timedelta(timedelta=self.recur)}"
                )
            footer = "Next runtime:"
        else:
            try:
                fmt_date = next_run_at.strftime("%A %B %-d, %Y at %-I%p %Z")
            except ValueError:  # Windows
                # This looks less natural, but I'm not doing this piecemeal to emulate.
                fmt_date = next_run_at.strftime("%A %B %d, %Y at %I%p %Z")
            description = f"{self.nicename} will run at {fmt_date}."
            footer = "Runtime:"

        embed.set_footer(text=footer)
        embed.description = description
        return embed

    def update_objects(self, bot):
        """ Updates objects or throws an AttributeError """
        guild_id = self.author.guild.id
        author_id = self.author.id
        channel_id = self.channel.id

        guild = bot.get_guild(guild_id)
        self.author = guild.get_member(author_id)
        self.channel = guild.get_channel(channel_id)
        if not hasattr(self.channel, "id"):
            raise AttributeError()
        # Yes, this is slower than an inline `self.channel.id`
        # It's also not slow anywhere important, and I prefer the clear intent
