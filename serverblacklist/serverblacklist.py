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
    __version__ = "0.2"

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


    @checks.is_owner()
    @commands.group(name="blacklistset", pass_context=True)
    async def blacklistset(self, ctx):
        """Manage the server blacklist
        These commands will fail if not in direct message"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @blacklistset.command(name="fetch", pass_context=True)
    async def fetch_blacklist(self, ctx):
        """get a list of blacklisted server's IDs"""

        if ctx.message.channel.is_private:
            keys = ""
            for key in self.bot.settings.items():
                if is_number(key):
                    keys = keys.join("{} ,".format(key))
            keys = keys[:-1]
            await self.bot.say("Here are the server IDs in the blacklist: \n"
                               "{}".format(keys))
        else:
            await self.bot.say("You can't use that here.")



    @checks.is_owner()
    @blacklistset.command(name="setmsg", pass_context=True)
    async def setleaveonblack(self, ctx, msg=None):
        """sets (or clears) the message to send when leaving
        like the rest of this cog, direct message only
        message must be enclsed in quotes"""

        if ctx.message.channel.is_private:
            self.settings['msg'] = msg
            self.save_json
            if msg:
                await self.bot.say("Message set to: \n```{}```".format(msg))
            else:
                await self.bot.say("Leave message disabled")
        else:
            await self.bot.say("You can't use that here.")



    async def blacklist_routine(self, server):
        """do the thing"""

        if server.id in self.settings:
            if self.settings['msg']:
                self.bot.send_message(server, "{}".format(msg))
            await self.bot.leave_server(server)
            log.debug("I left a server named {} with an ID of {} "
                      "".format(server.name, server.id))


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
        pass

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
