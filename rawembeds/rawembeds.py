import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import ast


class RawEmbeds:
    """
    """

    __author__ = "mikeshardmind"
    __version__ = "1.1"

    def __init__(self, bot):

        self.bot = bot
        self.embeds = dataIO.load_json('data/rawembeds/embeds.json')

    def save_embeds(self):
        dataIO.save_json("data/embedmaker/embeds.json", self.embeds)

    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.command(name="grabrawembed", hidden=True, pass_context=True)
    async def grabrawembed(self, ctx, name: str):
        data = self.embeds.get(name, None)
        if data is None:
            return

        em = discord.Embed(**data)
        await self.bot.say(embed=em)

    @commands.command(name="dmrawembed", hidden=True, pass_context=True)
    async def dmrawembed(self, ctx, name: str):
        data = self.embeds.get(name, None)
        if data is None:
            return

        em = discord.Embed(**data)
        await self.bot.send_message(ctx.message.author, embed=em)

    @checks.is_owner()
    @commands.command(name="makerawembed", hidden=True, pass_context=True)
    async def makerawembed(self, ctx, name: str, *, embed_dict: str):

        data = ast.literal_eval(embed_dict)
        if isinstance(data, dict):
            em = discord.Embed(**data)
            self.embeds.update({name: em.to_dict()})
            self.save_embeds()
            await self.bot.say(embed=em)


def check_folder():
    f = 'data/rawembeds'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/rawembeds/embeds.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = RawEmbeds(bot)
    bot.add_cog(n)
