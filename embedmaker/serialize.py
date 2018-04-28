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
    'fields': []
}


def serialize_embed(embed: discord.Embed) -> dict:

    ret = {
        'initable': {},
        'settable': {}
    }

    for k in template['initable'].keys():
        v = getattr(embed, k, None) or None
        if k == 'timestamp' and v:
            v = v.timestamp()
        ret['initable'][k] = v

    for k, v in template['settable'].items():
        proxy = getattr(embed, k, None)

        ret['settable'][k] = {}
        for attr in v.keys():
            ret['settable'][k][attr] = getattr(
                proxy, attr, None
            ) or None

    ret['fields'] = []
    for field in embed.fields:
        data = {}
        for attr in ['name', 'value', 'inline']:
            v = getattr(field, attr, None) or None
            if v:
                data[attr] = v

        if data:
            ret['fields'].append(data)

    return ret


def deserialize_embed(conf: dict) -> discord.Embed:

    unpack = copy(conf['initable'])

    if unpack['timestamp'] is not None:
        unpack['timestamp'] = dt.utcfromtimestamp(unpack['timestamp'])

    e = discord.Embed(**unpack)

    for k, v in conf['settable'].items():
        getattr(e, 'set_' + k)(**v)

    for f in conf['fields']:
        e.add_field(**f)

    return e
