import os
import sys
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks


class Resourcer:
    """Custom cog for storing a callable embed"""

    __author__ = "mikeshardmind"
    __version__ = "0.2"

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.group(name="rset", pass_context=True)

    

    async def embedsend(self, ctx, channel_id=None):
        """sends an embed to the channel given"""
        author = ctx.message.author
        channel = ctx.message.channel


        if channel.is_private:
            if channel_id:
                dest=None
                for serv in self.bot.servers:
                    for chan in serv.channels:
                        if channel_id == chan.id:
                            dest = chan
                if dest:
                    await self.bot.say("Please give me the message to be embedded.")
                    message = await self.bot.wait_for_message(channel=channel, author=author)

                    content = message.clean_content
                    author = message.author
                    timestamp = message.timestamp.strftime('%Y-%m-%d %H:%M')
                    avatar = author.avatar_url if author.avatar else author.default_avatar_url
                    footer = 'last updated: {}'.format(timestamp)
                    em = discord.Embed(description=content, color=discord.Color.purple())
                    em.set_author(name='Alliance Resources')
                    em.set_footer(text=footer)

                    if channel.permissions_for(self.bot.user).send_messages:
                        if channel.permissions_for(self.bot.user).embed_links:
                            await self.bot.send_message(dest, embed=em)

                else:
                    await self.bot.say("I can't find that channel")
            else:
                await self.bot.say("I need a channel ID")
        else:
            await self.bot.say("You can't use this here")

def check_folder():
    f = 'data/resourcer'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/resourcer/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    n = Embedder(bot)
    bot.add_cog(n)
