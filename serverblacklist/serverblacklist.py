import os
import sys  # noqa: F401
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
    __version__ = "0.3"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/serverblacklist/settings.json')
        self.blacklist = dataIO.load_json('data/serverblacklist/list.json')

    def save_json(self):
        dataIO.save_json("data/serverblacklist/settings.json", self.settings)
        dataIO.save_json("data/serverblacklist/list.json", self.blacklist)

    @checks.is_owner()
    @commands.group(name="serverblacklist", pass_context=True)
    async def serverblacklist(self, ctx):
        """Manage the server blacklist
        These commands will fail if not in direct message"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.is_owner()
    @serverblacklist.command(name="add", pass_context=True)
    async def blacklist_server(self, ctx, server_id=None):
        """blacklists a server by server ID
        because the author is lazy,
        this must be used in direct messages"""

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't blacklist a server without the ID")
            else:
                if server_id not in self.blacklist:
                    self.blacklist[server_id] = {}
                    self.save_json()
                    await self.bot.say("Server with ID: {} "
                                       "blacklisted.".format(server_id))
                    in_server = False
                    serv_ids = map(lambda s: s.id, self.bot.servers)
                    for serv_id in serv_ids:
                        if serv_id in self.blacklist:
                            in_server = True
                    if in_server:
                        server = self.bot.get_server(server_id)
                        channel = server.default_channel
                        msg = self.settings.get('msg', None)
                        if msg:
                            if channel.permissions_for(
                                                      server.me).send_messages:
                                await self.bot.send_message(channel,
                                                            "{}".format(msg))
                            else:
                                log.debug("Did not have permission to "
                                          "leave exit message for"
                                          "server named {} with an ID of {}"
                                          .format(server.name, server.id))
                        await asyncio.sleep(1)
                        await self.bot.leave_server(server)
                        await self.bot.say("I was in that server. Was.")
                else:
                    await self.bot.say("That server is already "
                                       "in the blacklist")
        else:
            try:
                await self.bot.say("You can't use that here")
            except discord.errors.Forbidden:
                log.debug("Some Dumbass didn't RTFM and tried to use me in a "
                          "place I couldn't resond")

    @checks.is_owner()
    @serverblacklist.command(name="remove", pass_context=True)
    async def un_blacklist_server(self, ctx, server_id=None):
        """un-blacklists a server by ID
        for the sake of consistency,
        this can only be used in direct messages"""

        if ctx.message.channel.is_private:
            if server_id is None:
                await self.bot.say("I can't remove a server from the blacklist"
                                   " without an ID")
            else:
                if server_id in list(self.blacklist):
                    del self.blacklist[server_id]
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
    @serverblacklist.command(name="list", pass_context=True)
    async def fetch_blacklist(self, ctx):
        """get a list of blacklisted server's IDs"""

        if ctx.message.channel.is_private:

            keys = " ,".join(self.blacklist.keys())

            if keys:
                await self.bot.say("Here are the server IDs "
                                   "in the blacklist: \n"
                                   "{}".format(keys))
            else:
                await self.bot.say("There are no servers in the blacklist.")
        else:
            await self.bot.say("You can't use that here.")

    @checks.is_owner()
    @serverblacklist.command(name="setmsg", pass_context=True)
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
        channel = server.default_channel

        if server.id in self.blacklist:
            msg = self.settings.get('msg', None)
            if msg:
                if channel.permissions_for(server.me).send_messages:
                    await self.bot.send_message(channel, "{}".format(msg))
                else:
                    log.debug("Did not have permission to leave exit message "
                              "for server named {} with an ID of {} "
                              "".format(server.name, server.id))
            await asyncio.sleep(1)
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
    f = 'data/serverblacklist/list.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = ServerBlacklist(bot)
    bot.add_listener(n.blacklist_routine, "on_server_join")
    bot.add_cog(n)
