from typing import List
import discord
from redbot.core.bot import Red


class NwayRelay:

    def __init__(self, *, channels: List[discord.TextChannel]):
        self.channels = channels

    def get_destinations(self, message: discord.Message):
        if message.channel not in self.channels:
            return []
        return [
            c for c in self.channels if c != message.channel
        ]

    @classmethod
    def from_data(cls, bot: Red, channels: List[int]):
        channel_objs = [
            c for c in bot.get_all_channels()
            if c.id in channels
        ]
        return cls(channels=channel_objs)

    def to_data(self):
        return {'channels': [c.id for c in self.channels]}


class OnewayRelay:

    def __init__(self, *,
                 source: discord.TextChannel,
                 destinations: List[discord.TextChannel]):
        self.source = source
        self.destinations = destinations

    def get_destinations(self, message: discord.Message):
        if message.channel != self.source:
            return []
        return [
            d for d in self.destinations if d != message.source
        ]

    @classmethod
    def from_data(cls, bot: Red, *, source: int, destinations: List[int]):
        source_obj = discord.utils.get(bot.get_all_channels(), id=source)
        destination_objs = [
            c for c in bot.get_all_channels()
            if c.id in destinations
        ]
        return cls(source=source_obj, destinations=destination_objs)

    def to_data(self):
        return {
            'source': self.source.id,
            'destinations': [c.id for c in self.destinations]
        }
