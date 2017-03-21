import os
import sys
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks

log = logging.getLogger('red.ServerBlacklist')

class ServerBlacklist:
    """Lets a bot owner create a list of servers that the bot will immediately
    leave when joined to. It does not require you to make the bot private"""

    __author__ = "mikeshardmind"
    __version__ = "0.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/serverblacklist/settings.json')

    def save_json(self):
        dataIO.save_json("data/serverblacklist/settings.json", self.settings)


    @checks.is_owner()
    @commands.command(name="blacklistserver", pass_context=True)
    async def blacklist_server(self, ctx, server_id=None):
        """blacklists a server by server ID
        because the author is lazy,
        this must be used in direct messages"""

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't blacklist a server without the ID")
            else:
                if server_id not in self.settings:
                    self.settings[server_id] = {'listed': True}
                    self.save_json()
                    await self.bot.say("Server with ID: {} "
                                       "blacklisted.".format(server_id))
                    serv_ids = map(lambda s: s.id, self.bot.servers)
                    for serv_id in serv_ids:
                        if serv_id in self.settings:
                            server = self.bot.get_server(server_id)
                            await self.bot.leave_server(server)
                            await self.bot.say("I was in that server. Was.")
                else:
                    await self.bot.say("That server is already in the blacklist")
        else:
            try:
                await self.bot.say("You can't use that here")
            except discord.errors.Forbidden:
                log.debug("Some Dumbass didn't RTFM and tried to use me in a "
                          "place I couldn't resond")


    @checks.is_owner()
    @commands.command(name="unblacklistserver", pass_context=True)
    async def un_blacklist_server(self, ctx, server_id=None):
        """un-blacklists a server by ID
        for the sake of consistency,
        this can only be used in direct messages"""

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't remove a server from the blacklist"
                                   " without an ID")
            else:
                if server_id in list(self.settings):
                    del self.settings[server_id]
                    self.save_json()
                    await self.bot.say("Server with ID: {} no longer "
                                       "in blacklist".format(server_id))
                else:
                    await self.bot.say("There wasn't a server with that ID "
                                       "in the blacklist")
        else:
            try:
                await self.bot.say("You can't use that here")
            except discord.errors.Forbidden:
                log.debug("Some Dumbass didn't RTFM and tried to use me in a "
                          "place I couldn't resond")


    async def blacklist_routine(self, server):
        """do the thing"""

        if server.id in self.settings:
            await self.bot.leave_server(server)
            log.debug("I left a server named {} with an ID of {} "
                      "".format(server.name, server.id))


def check_folder():
    f = 'data/serverblacklist'
    if not os.path.exists(f):
        os.makedirs(f)

def check_file():
    f = 'data/serverblacklist/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})

def setup(bot):
    check_folder()
    check_file()
    n = ServerBlacklist(bot)
    bot.add_listener(n.blacklist_routine, "on_server_join")
    bot.add_cog(n)
