import discord
from redbot.core import RedContext
from .serializers import deserialize_embed


class InteractiveCreator:

    settable_attrs = (
        'author',
        'title',
        'description',
        'color',
        'footer',
        'image',
        'timestamp',
        'url',
        'thumbnail',
        'fields'
    )

    def __init__(self, *, ctx: RedContext, name: str):
        self.ctx = ctx
        self.name = name
        self.em_dict = {}

    @property
    def embed(self):
        return deserialize_embed(self.em_dict)

    async def send(self):
        await self.ctx.send(self.embed)

    async def main_menu(self):
        pass
