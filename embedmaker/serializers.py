import discord
from datetime import datetime


def deserialize_embed(data: dict):
    """
    provides a method for deserializing stored embeds
    """

    can_init = ('title', 'description', 'url', 'color')
    iset = {
        k: v for k, v in data.items()
        if k in can_init
        and v is not None
    }
    if 'timestamp' in data:
        iset['timestamp'] = datetime.strptime(
            data['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'
        )

    ret = discord.Embed(**iset)

    if 'footer' in data:
        ret.set_footer(
            **data['footer']
        )
    if 'image' in data:
        ret.set_image(
            **data['image']
        )
    if 'thumbnail' in data:
        ret.set_thumbnail(
            **data['thumbnail']
        )
    if 'author' in data:
        ret.set_author(
            **data['author']
        )
    for field in data.get('fields', []):
        ret.add_field(
            **field
        )

    return ret


def serialize_embed(embed: discord.Embed):
    """
    serializes an embed
    """

    ret = {}

    ret['title'] = embed.title if embed.title else None
    ret['description'] = embed.description if embed.description else None
    ret['timestamp'] = embed.timestamp.strftime(
        '%Y-%m-%dT%H:%M:%S.%f'
    ) if embed.timestamp else None
    ret['url'] = embed.url if embed.url else None
    ret['color'] = embed.color if embed.color else None

    if embed.author:
        a = {}
        if embed.author.name:
            a['name'] = embed.author.name
        if embed.author.url:
            a['url'] = embed.author.url
        if embed.author.icon_url:
            a['icon_url'] = embed.author.icon_url

        ret.update({'author': a})

    if embed.image:
        ret.update(
            {'image': {'url': embed.image.url}}
        )
    if embed.thumbnail:
        ret.update(
            {'thumbnail': {'url': embed.thumbnail.url}}
        )

    ret['fields'] = [
        {
            'name': f.name,
            'value': f.value,
            'inline': f.inline
        } for f in embed.fields
    ]

    return ret
