from datetime import datetime
import logging
import discord
from redbot.core import commands
import asyncio


def neuter_coroutines(klass):
    # I might forget to modify this with discord.py updates, so lets automate it.

    for attr in dir(klass):
        _ = getattr(klass, attr, None)
        if attr != "_dummy_coro" and asyncio.iscoroutinefunction(_):

            def getter(self):
                return self._dummy_coro

            setattr(klass, attr, getter)


@neuter_coroutines
class SchedulerMessage(discord.Message):
    """
    Subclassed discord message with neutered coroutines.

    Extremely butchered class for a specific use case.
    Be careful when using this in other use cases.
    """

    def __init__(
        self,
        *,
        content: str,
        author: discord.User,
        channel: discord.TextChannel,
        guild: discord.Guild = None,
    ) -> None:
        self.id = discord.utils.time_snowflake(datetime.utcnow())
        self.author = author
        self.channel = channel
        self.call = None
        data = {
            "mention_everyone": bool(
                "@everyone" in content
                and channel.permissions_for(author).mention_everyone
            ),
            "content": content,
            "type": 0,
        }
        self._update(channel, data)

    def _update(self, channel, data):
        self.channel = channel
        self._try_patch(data, "mention_everyone")
        self._try_patch(
            data, "type", lambda x: discord.enums.try_enum(discord.MessageType, x)
        )
        self._try_patch(data, "content")
        self._try_patch(data, "attachments", lambda x: [])
        self._try_patch(data, "embeds", lambda x: [])

        for handler in ("author", "mentions", "mention_roles"):
            try:
                getattr(self, "_handle_%s" % handler)(data[handler])
            except KeyError:
                continue

        # clear the cached properties
        cached = filter(lambda attr: attr.startswith("_cs_"), self.__slots__)
        for attr in cached:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    async def _dummy_coro(self, *_args, **_kwargs) -> None:
        pass
