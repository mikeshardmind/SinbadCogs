from typing import List
import discord
from redbot.core.bot import Red


class NwayRelay:
    def __init__(self, *, bot: Red, channels: List[int]) -> None:
        self.channel_ids: List[int] = channels
        self.bot = bot

    @property
    def channels(self) -> List[discord.TextChannel]:
        ret: List[discord.TextChannel] = []
        for idx in self.channel_ids:
            c = self.bot.get_channel(idx)
            if c:
                ret.append(c)
        return ret

    def get_destinations(self, message: discord.Message) -> List[discord.TextChannel]:
        if message.channel.id not in self.channels:
            return []
        ret: List[discord.TextChannel] = []
        for idx in self.channel_ids:
            if idx == message.channel.id:
                continue
            c = self.bot.get_channel(idx)
            if c:
                ret.append(c)
        return ret

    def to_data(self):
        return {"channels": self.channel_ids}


class OnewayRelay:
    def __init__(self, *, bot: Red, source: int, destinations: List[int]) -> None:
        self.source_id: int = source
        self.destination_ids: List[int] = destinations
        self.bot: Red = bot

    @property
    def source(self) -> discord.TextChannel:
        return self.bot.get_channel(self.source_id)

    @property
    def destinations(self) -> List[discord.TextChannel]:
        ret: List[discord.TextChannel] = []
        for idx in self.destination_ids:
            c = self.bot.get_channel(idx)
            if c:
                ret.append(c)
        return ret

    def get_destinations(self, message: discord.Message) -> List[discord.TextChannel]:
        if message.channel.id != self.source_id:
            return []
        ret: List[discord.TextChannel] = []
        for idx in self.destination_ids:
            if idx == message.channel.id:
                continue
            c = self.bot.get_channel(idx)
            if c:
                ret.append(c)
        return ret

    def to_data(self):
        return {"source": self.source_id, "destinations": self.destination_ids}
