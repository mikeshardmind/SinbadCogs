from __future__ import annotations

import re
from typing import List, TypeVar, Iterable, Union, Iterator, cast

import discord
from redbot.core.bot import Red
from redbot.core.utils.common_filters import INVITE_URL_RE


def role_mention_cleanup(message: discord.Message) -> Union[str, None]:

    content = message.content

    if not content:
        return None

    assert isinstance(content, str), "Message.content got screwed somehow..."  # nosec

    if message.guild is None:
        return content

    transformations = {
        re.escape("<@&{0.id}>".format(role)): "@" + role.name
        for role in message.role_mentions
    }

    def repl(obj):
        return transformations.get(re.escape(obj.group(0)), "")

    pattern = re.compile("|".join(transformations.keys()))
    result = pattern.sub(repl, content)

    return result


def embed_from_msg(message: discord.Message, filter_invites=False) -> discord.Embed:
    channel = cast(discord.TextChannel, message.channel)
    server = channel.guild
    content = role_mention_cleanup(message)
    if filter_invites and content:
        content = INVITE_URL_RE.sub("[SCRUBBED INVITE]", content)
    author = message.author
    sname = server.name
    cname = channel.name
    avatar = author.avatar_url
    footer = "Said in {} #{}".format(sname, cname)
    em = discord.Embed(
        description=content, color=author.color, timestamp=message.created_at
    )
    em.set_author(name="{}".format(author.name), icon_url=avatar)
    em.set_footer(text=footer, icon_url=server.icon_url)
    if message.attachments:
        a = message.attachments[0]
        fname = a.filename
        url = a.url
        if fname.split(".")[-1] in ["png", "jpg", "gif", "jpeg"]:
            em.set_image(url=url)
        else:
            em.add_field(
                name="Message has an attachment",
                value="[{}]({})".format(fname, url),
                inline=True,
            )

    return em


T = TypeVar("T")


def unique(a: Iterable[T]) -> List[T]:
    ret: List[T] = []
    for item in a:
        if item not in ret:
            ret.append(item)
    return ret


def txt_channel_finder(bot: Red, chaninfo: str) -> List[discord.TextChannel]:
    """
    custom text channel finder
    """
    _id_regex = re.compile(r"([0-9]{15,21})$")

    def _get_id_match(argument):
        return _id_regex.match(argument)

    match = _get_id_match(chaninfo) or re.match(r"<#?([0-9]+)>$", chaninfo)

    def txt_check(c):
        return c.id == int(match.group(1)) if match is not None else c.name == chaninfo

    def all_text() -> Iterator[discord.TextChannel]:
        for guild in bot.guilds:
            yield from guild.text_channels

    return [c for c in all_text() if txt_check(c)]
