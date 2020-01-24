from __future__ import annotations

import re

import discord
import yaml
import yaml.reader
from redbot.core import commands

from .serialize import template, deserialize_embed
from .time_utils import parse_time

yaml.reader.Reader.NON_PRINTABLE = re.compile(
    "[^\x09\x0A\x0D\x20-\x7E\x85\xA0-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)

START_YAML_BLOCK_RE = re.compile(r"^((```yaml)(?=\s)|(```))")


def string_preprocessor(user_input: str) -> str:
    s = user_input.strip()
    if s.startswith("```") and s.endswith("```"):
        s = START_YAML_BLOCK_RE.sub("", s)[:-3]
    return s


def handle_timestamp(to_set) -> float:
    ts: float
    try:
        ts = parse_time(to_set).timestamp()
    except Exception:
        ts = float(to_set)

    return ts


# TODO: Pull the logic out of d.py converter to not do this here...
async def handle_color(ctx, to_set) -> int:
    x: int
    try:
        conv = discord.ext.commands.ColourConverter()
        x = (await conv.convert(ctx, to_set)).value
    except Exception:
        if isinstance(to_set, str) and to_set.startswith("#"):
            x = int(to_set.lstrip("#"), 16)
        else:
            x = int(to_set)

    return x


# TODO : Use schema here. Will allow giving back reasonable error messages on failures.
async def embed_from_userstr(ctx: commands.Context, string: str) -> discord.Embed:
    ret: dict = {"initable": {}, "settable": {}, "fields": []}
    string = string_preprocessor(string)

    parsed = yaml.safe_load(string)
    ret["fields"] = [
        field_data for _index, field_data in sorted(parsed.get("fields", {}).items())
    ]

    for outer_key in ["initable", "settable"]:
        for inner_key in template[outer_key].keys():
            to_set = parsed.get(inner_key, {})
            if to_set:
                if inner_key == "timestamp":
                    to_set = handle_timestamp(to_set)
                elif inner_key in ("color", "colour"):
                    to_set = await handle_color(ctx, to_set)

                ret[outer_key][inner_key] = to_set

    return deserialize_embed(ret)
