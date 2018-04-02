import discord
from redbot.core import RedContext


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

    async def main_menu(self):
        pass