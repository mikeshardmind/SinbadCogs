from __future__ import annotations

from datetime import datetime as dt

import discord

# This exists because
# `discord.Embed(**discord.Embed().to_dict())`
# fails in hillarious ways when dealing with any embed
# containing a `discord.Embed.Empty()`

template: dict = {
    "initable": {
        "description": None,
        "color": None,
        "title": None,
        "url": None,
        "timestamp": None,
    },
    "settable": {
        "image": {"url": None},
        "thumbnail": {"url": None},
        "author": {"url": None, "name": None, "icon_url": None},
        "footer": {"text": None, "icon_url": None},
    },
    "fields": [],
}


def serialize_embed(embed: discord.Embed) -> dict:

    ret: dict = {"initable": {}, "settable": {}}

    for k in template["initable"].keys():
        v = getattr(embed, k, None) or None
        if v is None:
            continue
        if k == "timestamp" and v:
            v = v.timestamp()
        if k == "color" and v:
            v = v.value
        ret["initable"][k] = v

    for k, v in template["settable"].items():
        proxy = getattr(embed, k, None) or None
        if proxy is None:
            continue
        ret["settable"][k] = {}
        for attr in v.keys():
            to_set = getattr(proxy, attr, None)
            if to_set or to_set is False:  # specifically not None or embed.Empty
                ret["settable"][k][attr] = to_set

    ret["fields"] = []
    for field in embed.fields:
        data = {}
        for attr in ["name", "value", "inline"]:
            to_set = getattr(field, attr, None)
            if to_set or to_set is False:  # specifically not None or embed.Empty
                data[attr] = to_set
        if data:
            ret["fields"].append(data)

    return ret


def deserialize_embed(conf: dict) -> discord.Embed:

    unpack = {k: v for k, v in conf["initable"].items() if v}

    if "timestamp" in unpack:
        unpack["timestamp"] = dt.utcfromtimestamp(unpack["timestamp"])

    e = discord.Embed(**unpack)

    for k, v in conf["settable"].items():
        if v is not None:
            to_set = {_k: _v for _k, _v in v.items() if _v}
            getattr(e, "set_" + k)(**to_set)

    for f in conf["fields"]:
        e.add_field(**f)

    return e
