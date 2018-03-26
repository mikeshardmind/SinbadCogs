import discord
from datetime import datetime


class ConfigEmbed:

    def __init__(self, embed: discord.Embed):
        self.embed = embed

    @classmethod
    def from_config(cls, data: dict):
        try:
            timestamp = data['timestamp']
        except KeyError:
            pass
        else:
            data['timestamp'] = datetime.strptime(
                timestamp, '%Y-%m-%dT%H:%M:%S.%f')
        em = discord.Embed(**data)
        return cls(em)
