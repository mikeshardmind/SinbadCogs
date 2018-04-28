import discord
from datetime import datetime as dt


def serialize_embed(embed: discord.Embed) -> dict:
    data = embed.to_dict()
    if embed.timestamp:
        data['timestamp'] = embed.timestamp.timestamp()


def deserialize_embed(conf: dict) -> discord.Embed:

    unpack = {
        k: v for k, v in conf
        if k in (
            'description',
            'color',
            'title',
            'url',
            'timestamp'
        )
    }

    settable = {
        k: v for k, v in conf
        if k in (
            'image',
            'thumbnail',
            'author',
            'footer'
        )
    }

    if unpack.get('timestamp', None):
        unpack['timestamp'] = dt.utcfromtimestamp(unpack['timestamp'])

    e = discord.Embed(**unpack)

    for k, v in {settable.items()}:
        getattr(e, 'set_' + k)(**v)

    for field in conf.get('fields', []):
        e.add_field(**field)

    return e
