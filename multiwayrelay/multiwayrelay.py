import os
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import re
import logging
import itertools

log = logging.getLogger('red.MultiWayRelay')


class MultiWayRelay:
    """
    hmmmm
    """

    __author__ = "mikeshardmind"
    __version__ = "1.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/multiwayrelay/settings.json')
        self.links = {}
        self.activechans = []
        self.initialized = False

    def save_json(self):
        dataIO.save_json("data/multiwayrelay/settings.json", self.settings)

    @checks.is_owner()
    @commands.command(name="makerelay", pass_context=True)
    async def makelink(self, ctx, name: str, *chanids: str):
        """takes a name (no whitespace) and a list of channel ids"""
        name = name.lower()
        if name in self.settings:
            return await self.bot.say("that name is in use")

        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]
        channels = [c.id for c in channels if c.id in chanids]

        if any(i in self.activechans for i in channels):
            await self.bot.say("Warning: One or more of these channels is "
                               "already linked elsewhere")

        channels = unique(channels)

        if len(channels) >= 2:
            self.settings[name] = {'chans': channels}
            self.save_json()
            await self.validate()
            if name in self.links:
                await self.bot.say("Relay formed.")
        else:
            await self.bot.say("I did not get two or more valid channel IDs")

    @checks.is_owner()
    @commands.command(name="addtorelay", pass_context=True)
    async def addtorelay(self, ctx, name: str, *chanids: str):
        """add chans to a relay"""

        name = name.lower()
        if name in self.settings:
            return await self.bot.say("that relay doesnt exist")

        chanids += self.settings[name]['chans']
        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]
        channels = [c.id for c in channels if c.id in chanids]

        if any(i in self.activechans for i in channels):
            await self.bot.say("Warning: One or more of these channels is "
                               "already linked elsewhere")

        channels = unique(channels)

        self.settings[name] = {'chans': channels}
        self.save_json()
        await self.validate()
        await self.bot.say("Relay updated.")

    @checks.is_owner()
    @commands.command(name="remfromrelay", pass_context=True)
    async def remfromrelay(self, ctx, name: str, *chanids: str):
        """remove chans from a relay"""

        name = name.lower()
        if name in self.settings:
            return await self.bot.say("that relay doesnt exist")

        self.settings[name]['chans']
        for cid in chanids:
            if cid in self.settings[name]['chans']:
                self.settings[name]['chans'].remove(cid)

        self.save_json()
        await self.validate()
        await self.bot.say("Relay updated.")

    @checks.is_owner()
    @commands.command(name="remrelay", pass_context=True)
    async def unlink(self, ctx, name: str):
        """removes a relay by name"""
        name = name.lower()
        if name in self.links:
            chans = self.links[name]
            self.activechans = [cid for cid in self.activechans
                                if cid not in [c.id for c in chans]]
            self.links.pop(name, None)
            self.settings.pop(name, None)
            self.save_json()
            await self.bot.say("Relay removed")
        else:
            await self.bot.say("No such relay")

    @checks.is_owner()
    @commands.command(name="listrelays", pass_context=True)
    async def list_links(self, ctx):
        """lists the channel links by name"""

        links = list(self.settings.keys())
        await self.bot.say("Active relay names:\n {}".format(links))

    async def validate(self):
        channels = self.bot.get_all_channels()
        channels = [c for c in channels if c.type == discord.ChannelType.text]

        for name in self.settings:
            chan_ids = list(*self.settings[name].values())
            chans = [c for c in channels if c.id in chan_ids]
            self.links[name] = chans
            self.activechans += chan_ids

    async def do_stuff_on_message(self, message):
        """Do stuff based on settings"""
        if not self.initialized:
            await self.validate()
            self.initialized = True

        if message.author != self.bot.user:

            channel = message.channel
            destinations = []
            for link in self.links:
                if channel in self.links[link]:
                    destinations = [c for c in self.links[link]
                                    if c != channel]

            for destination in destinations:
                await self.sender(destination, message)

    async def sender(self, where, message=None):
        """sends the thing"""

        if message:
            em = self.qform(message)
            try:
                await self.bot.send_message(where, embed=em)
            except Exception as e:
                log.debug("{}".format(e))

    def role_mention_cleanup(self, message):

        if message.server is None:
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

    def qform(self, message):
        channel = message.channel
        server = channel.server
        content = message.content
        author = message.author
        sname = server.name
        cname = channel.name
        avatar = author.avatar_url if author.avatar \
            else author.default_avatar_url
        footer = 'Said in {} #{}'.format(sname, cname)
        em = discord.Embed(description=content, color=author.color,
                           timestamp=message.timestamp)
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


def check_folder():
    f = 'data/multiwayrelay'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/multiwayrelay/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = MultiWayRelay(bot)
    bot.add_listener(n.do_stuff_on_message, "on_message")
    bot.add_cog(n)
