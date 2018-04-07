import discord
import re
import itertools


def role_mention_cleanup(self, message):

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


def embed_from_msg(message: discord.Message):
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
        fname = a['filename']
        url = a['url']
        if fname.split('.')[-1] in ['png', 'jpg', 'gif', 'jpeg']:
            em.set_image(url=url)
        else:
            em.add_field(name='Message has an attachment',
                         value='[{}]({})'.format(fname, url),
                         inline=True)

    return em


def unique(a):
    indices = sorted(range(len(a)), key=a.__getitem__)
    indices = set(next(it) for k, it in
                  itertools.groupby(indices, key=a.__getitem__))
    return [x for i, x in enumerate(a) if i in indices]
