import discord
from .helpers import embed_from_msg


class NwayRelay:

    def __init__(self, *channels: discord.TextChannel):
        self.channels = channels

    async def relay(self, message: discord.Message):
        if message.channel not in self.channels:
            return
        for d in self.channels:
            if d == message.channel:
                continue
            await d.send(
                embed=embed_from_msg(message)
            )


class OnewayRelay:

    def __init__(self, source: discord.TextChannel,
                 *destinations: discord.TextChannel):
        self.source = source
        self.destinations = destinations

    async def relay(self, message: discord.Message):
        if message.channel != self.source:
            return
        for d in self.destinations:
            await d.send(
                embed=embed_from_msg(message)
            )
