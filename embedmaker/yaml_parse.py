import yaml
import yaml.reader
import re

import discord

from redbot.core import commands
from .serialize import template, deserialize_embed
from .utils import parse_time

yaml.reader.Reader.NON_PRINTABLE = re.compile(
    "[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)


# TODO : Document failure cases of this for proper exception handling.
# noinspection PyBroadException
async def embed_from_userstr(ctx: commands.Context, string: str) -> discord.Embed:
    ret = {"initable": {}, "settable": {}, "fields": []}
    string = string.strip()
    if string.startswith("```") and string.endswith("```"):
        string = "\n".join(string.split("\n")[1:-1])

    parsed = yaml.safe_load(string)
    ret["fields"] = [x[1] for x in sorted(parsed.get("fields", {}).items())]

    for outer_key in ["initable", "settable"]:
        for inner_key in template[outer_key].keys():
            to_set = parsed.get(inner_key, {})
            if to_set:
                if inner_key == "timestamp":
                    try:
                        to_set = parse_time(to_set).timestamp()
                    except Exception:
                        to_set = float(to_set)

                if inner_key in ["color", "colour"]:
                    try:
                        x = (
                            await commands.converter.ColourConverter().convert(
                                ctx, to_set
                            )
                        ).value
                    except Exception:
                        try:
                            if isinstance(to_set, str) and to_set.startswith("#"):
                                to_set = int(to_set.lstrip("#"), 16)
                            else:
                                to_set = int(to_set)
                        except Exception:
                            raise
                    else:
                        to_set = x

                ret[outer_key][inner_key] = to_set

    return deserialize_embed(ret)
