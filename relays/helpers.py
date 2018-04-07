import discord
from discord.ext import commands
from typing import List
import re


def role_mention_cleanup(message: discord.Message) -> str:

    if message.guild is None:
        return message.content

    transformations = {
        re.escape('<@&{0.id}>'.format(role)): '@' + role.name
        for role in message.role_mentions
    }

    def repl(obj):
        return transformations.get(re.escape(obj.group(0)), '')

    pattern = re.compile('|'.join(transformations.keys()))
    result = pattern.sub(repl, message.content)

    return result


def embed_from_msg(message: discord.Message) -> discord.Embed:
    channel = message.channel
    server = channel.guild
    content = role_mention_cleanup(message)
    author = message.author
    sname = server.name
    cname = channel.name
    avatar = author.avatar_url
    footer = 'Said in {} #{}'.format(sname, cname)
    em = discord.Embed(description=content, color=author.color,
                       timestamp=message.created_at)
    em.set_author(name='{}'.format(author.name), icon_url=avatar)
    em.set_footer(text=footer, icon_url=server.icon_url)
    if message.attachments:
        a = message.attachments[0]
        fname = a.filename
        url = a.url
        if fname.split('.')[-1] in ['png', 'jpg', 'gif', 'jpeg']:
            em.set_image(url=url)
        else:
            em.add_field(name='Message has an attachment',
                         value='[{}]({})'.format(fname, url),
                         inline=True)

    return em


def unique(a):
    ret = []
    for item in a:
        if item not in ret:
            ret.append(item)
    return ret


def txt_channel_finder(bot: commands.bot, chaninfo: str
                       ) -> List[discord.TextChannel]:
    """
    custom text channel finder
    """
    _id_regex = re.compile(r'([0-9]{15,21})$')

    def _get_id_match(argument):
        return _id_regex.match(argument)

    match = _get_id_match(chaninfo) or re.match(
        r'<#?([0-9]+)>$', chaninfo)

    if match is not None:
        def txt_check(c):
            return isinstance(
                c, discord.TextChannel
            ) and c.id == int(match.group(1))
    else:
        def txt_check(c):
            return isinstance(
                c, discord.TextChannel
            ) and c.name == chaninfo
    return list(filter(txt_check, bot.get_all_channels()))
