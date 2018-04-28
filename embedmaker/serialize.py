import discord
from datetime import datetime as dt
from copy import copy

template = {
    'initable': {
        'description': None,
        'color': None,
        'title': None,
        'url': None,
        'timestamp': None
    },
    'settable': {
        'image': {'url': None},
        'thumbnail': {'url': None},
        'author': {'url': None, 'name': None, 'icon_url': None},
        'footer': {'text': None, 'icon_url': None}
    },
    'multiadded': {
        'fields': [],
    },
    'creator': None
}


def serialize_embed(embed: discord.Embed) -> dict:

    ret = {
        'initable': {},
        'settable': {},
        'multiadded': {}
    }
    data = embed.to_dict()

    for k, v in template.itmes():
        for attr in v.keys():
            if attr in data:
                ret[k][v][attr] = embed.timestamp.timestamp(
                ) if attr == 'timestamp' else data[k][v][attr]

    return ret


def deserialize_embed(conf: dict) -> discord.Embed:

    unpack = copy(conf['initable'])

    if 'timestamp' in unpack:
        unpack['timestamp'] = dt.utcfromtimestamp(unpack['timestamp'])

    e = discord.Embed(**unpack)

    for k, v in conf['settable'].items():
        getattr(e, 'set_' + k)(**v)

    # right now this is just fields, but why not just in case?
    for k, v in conf['multiadded'].items():
        for entry in v:
            getattr(e, 'add_{}'.format(k[:-1]))(**entry)

    return e
