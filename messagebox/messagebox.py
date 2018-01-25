import discord
import pathlib
from cogs.utils.dataIO import dataIO
from discord.ext import commands
from discord.utils import find
from .utils import checks
from typing import Union

path = 'data/messagebox'


class MessageBoxError(Exception):
    pass


class MessageBox:
    """
    replace builtin contact to log to a dedicated channel

    replacement rather than new command because some users get into habits
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0001)"

    def __init__(self, bot):
        self.bot = bot
        try:
            self.settings = dataIO.load_json(path + '/settings.json')
        except Exception:
            self.settings = {}
        if 'output' in self.settings:
            self.output = find(
                lambda m: m.id == self.settings['output'],
                self.bot.get_all_channels())

    def save_json(self):
        dataIO.save_json(path + '/settings.json', self.settings)

    def __unload(self):
        if oldcontact:
            self.bot.add_command(oldcontact)

    def get_servers(self, who: Union[discord.User, discord.Member]):
        shared_servers = []
        for server in self.bot.servers:
            x = server.get_member(who.id)
            if x is not None:
                shared_servers.append(server)
        return shared_servers

    @checks.is_owner()
    @commands.command(name='msgboxset', pass_context=True)
    async def msgboxset(self, ctx, channel: discord.Channel):
        """
        sets the channel where messages should be sent
        """
        self.settings['output'] = channel.id
        self.save_json()
        self.output = channel
        await self.bot.say('Output channel set to {}'.format(channel.mention))

    # more permissive since not DM
    @commands.cooldown(3, 60, commands.BucketType.user)
    @commands.command(name='contact', pass_context=True, aliases=['msgbox'])
    async def replacement_contact(self, ctx, *, message: str):
        """
        send a message to the bot owner
        """

        if len(message) == 0:
            return await self.bot.send_cmd_help(ctx)
        try:
            await self.process_message(ctx, message)
        except MessageBoxError as e:
            await self.bot.say('{}'.format(e))
        else:
            await self.bot.say('Message sent')

    async def process_message(self, ctx, message):

        if not self.output:
            raise MessageBoxError('My owner has not configured this')
            return
        if not self.output.permissions_for(self.output.server.me) >= \
                discord.Permissions(send_messages=True, embed_links=True):
            raise MessageBoxError('I can\'t send messages right now')
            return
        servers = self.get_servers(ctx.message.author)

        em = self.qform(ctx.message, servers, message)

        try:
            await self.bot.send_message(self.output, embed=em)
        except Exception:
            raise MessageBoxError(
                'Something unexpected went wrong. Please try again later')

    def qform(self, message, servers, content):
        channel = message.channel
        if channel.is_private:
            server = None
        else:
            server = channel.server
        author = message.author
        if server:
            footer = 'Sent from {} #{}'.format(server.name, channel.name)
            a_name = author.display_name
        else:
            footer = 'Sent from a direct message'
            a_name = author.name

        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url

        if isinstance(author, discord.Member):
            col = author.color
        else:
            col = discord.Color.dark_purple()
        em = discord.Embed(
            description=content, timestamp=message.timestamp, color=col)
        em.set_author(name='{}'.format(a_name), icon_url=avatar)
        em.set_footer(text=footer)
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
        em.add_field(name='Shared servers', inline=True,
                     value=", ".join([s.name for s in servers]))
        return em


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    n = MessageBox(bot)
    global oldcontact
    oldcontact = bot.get_command('contact')
    if oldcontact:
        bot.remove_command(oldcontact.name)
    bot.add_cog(n)
