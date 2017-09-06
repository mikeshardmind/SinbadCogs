import discord
from .utils import checks
from discord.ext import commands
from cogs.utils.dataIO import dataIO
import os
from datetime import datetime, timedelta
import random
from cogs.utils.chat_formatting import pagify
from typing import Union


class RaffleError(Exception):
    pass


class Raffle:
    def __init__(self, data=None):
        self.name = data.pop('name')
        self.server = data.pop('server')
        self.author = data.pop('author')
        self.starttime = data.pop('starttime').strftime("%Y-%m-%d %H:%M:%S")
        self.rolereq = data.pop('rolereq', None)
        self.minage = data.pop('minage')  # days
        self.locked = False
        self.registered = []

    def is_author(self, user: discord.Member):
        return self.author == user.id

    def is_old_enough(self, user: discord.Member):
        return (datetime.strptime(self.starttime, "%Y-%m-%d %H:%M:%S")
                - timedelta(days=self.minage)) > user.joined_at

    def has_role_required(self, user: discord.Member):
        if self.rolereq is None:
            return True
        else:
            return not set(self.rolereq).isdisjoint([r.id for r in user.roles])

    def to_dict(self):
        data = {
                'name': self.name,
                'server': self.server,
                'author': self.author,
                'starttime': self.starttime,
                'rolereq': self.rolereq,
                'minage': self.minage,
                'locked': self.locked,
                'registered': self.registered
               }
        return data

    def register(self, user: discord.Member):
        if not self.has_role_required(user):
            raise RaffleError("You don't have any of the required roles to "
                              "join this raffle")
        elif not self.is_old_enough(user):
            raise RaffleError("You haven't been a member of the server long "
                              "enough to join this raffle")
        elif user.id in self.registered:
            raise RaffleError("You are already registered for this giveaway")
        else:
            self.registered.append(user.id)


class Raffler:
    """Conditional Raffle"""

    __author__ = "mikeshardmind"
    __version__ = "1.0a"

    def __init__(self, bot):
        self.bot = bot
        self.raffles = dataIO.load_json('data/raffler/raffles.json')
        self.settings = dataIO.load_json('data/raffler/settings.json')

    def save_raffles(self):
        dataIO.save_json("data/raffler/raffles.json", self.raffles)

    def save_settings(self):
        dataIO.save_json("data/raffler/settings.json", self.settings)

    def init_settings(self, server: discord.Server):
        if server.id not in self.settings:
            self.settings[server.id] = {'minrole': None,
                                        'blacklisted': [],
                                        'max_concurrent': 1}
            self.save_settings()

    @commands.group(name="rafflerset", no_pm=True, pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def rafflerset(self, ctx):
        """settings for raffler"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @rafflerset.command(name="blacklist", no_pm=True, pass_context=True)
    async def raffler_blacklist(self, ctx,
                                bl: Union[discord.Member, discord.Role]):
        """adds a given user or role to the raffler blacklist"""
        server = ctx.message.server
        self.init_settings(server)
        if self.is_blacklisted(bl):
            return await self.bot.say("Already in blacklist")
        self.settings[server.id]['blacklisted'].append(bl.id)
        self.save_settings()
        await self.bot.say("Added them to the blacklist")

    @rafflerset.command(name="unblacklist", no_pm=True, pass_context=True)
    async def raffler_unblacklist(self, ctx,
                                  bl: Union[discord.Member, discord.Role]):
        """removes a given user or role from the blacklist"""
        server = ctx.message.server
        self.init_settings(server)
        if not self.is_blacklisted(bl):
            return await self.bot.say("They aren't blacklisted")
        self.settings[server.id]['blacklisted'].remove(bl.id)
        self.save_settings()
        await self.bot.say("Removed them from blacklist")

    @rafflerset.command(name="maxconcurrent", no_pm=True, pass_context=True)
    async def raffler_concurrent(self, ctx, num: int):
        """
        set the maximum concurrent giveaways by a single person
        (-1 for unlimited)
        """
        server = ctx.message.server
        self.init_settings(server)
        self.settings[server.id]['max_concurrent'] = num
        self.save_settings()
        await self.bot.say("Settings updated")

    @commands.group(name="raffle", no_pm=True, pass_context=True)
    @checks.mod_or_permissions(manage_server=True)
    async def raffler(self, ctx):
        """Giveaway tool"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @commands.cooldown(1, 300, commands.BucketType.user)
    @raffler.commnad(name="new", no_pm=True, pass_context=True)
    async def new_raffle(self, ctx, name: str,
                         minage: int, *roles: discord.Role):
        """
        makes a new raffle
        min age is the minimum number of days someone must be a part of the
        server to join the raffle
        if given a list of roles, people must have at least one of those
        to join. Mutli word roles need to be surrounded by quotation marks
        """

        server = ctx.message.server
        author = ctx.message.author
        self.init_settings(server)

        if self.is_blacklisted(author):
            return

        if self.user_concurrent(author) > \
                self.settings[server.id]['max_concurrent'] and \
                self.settings[server.id]['max_concurrent'] != -1:
            return await self.bot.say("You have reached the limit of active "
                                      "raffles")

        name = name.lower()
        if name in self.raffles[server.id]:
            return await self.bot.say("There is already a raffle by that name")

        data = {
                'name': name,
                'server': server.id,
                'author': author.id,
                'starttime': ctx.message.timestamp,
                'minage': minage
               }
        if len(roles) > 0:
            data.update({'rolereq': [r.id for r in roles]})
        raffle = Raffle(**data)

        self.raffles[server.id][name] = raffle
        await self.bot.say("Raffle started. People can join it with "
                           "`{}raffle join {}`".format(ctx.prefix, name))

    @raffler.command(name="join", pass_context=True, no_pm=True)
    async def join_raffle(self, ctx, name: str):
        """join an existing raffle by name"""
        server = ctx.message.server
        author = ctx.message.author
        self.init_settings(server)

        if self.is_blacklisted(author):
            return
        name = name.lower()
        if name not in self.raffles[server.id]:
            return await self.bot.say("No such raffle.")

        r = self.raffles[server.id][name]

        if r.locked:
            return await self.bot.say("That raffle is locked")

        try:
            r.register(author)
        except RaffleError as e:
            await self.bot.say("{}".format(e))
        else:
            await self.bot.say("You have been registered for this raffle.")
        self.save_raffles()

    @commands.cooldown(1, 300, commands.BucketType.user)
    @raffler.command(name="mention", pass_context=True,
                     no_pm=True, hidden=True)
    async def mention(self, ctx, name: str):
        server = ctx.message.server
        author = ctx.message.author
        channel = ctx.message.channel
        self.init_settings(server)

        name = name.lower()
        if name not in self.raffles[server.id]:
            return await self.bot.say("No such raffle.")
        r = self.raffles[server.id][name]
        entries = r.registered
        members = []
        for e in entries:
            x = server.get_member(e)
            if x is not None:
                members.append(x)

        output = ""
        if channel.permissions_for(author).mention_everyone:
            for member in members:
                output += "{0.mention} , ".format(member)
        else:
            for member in members:
                output += "\n{0.id}: {0.display_name}".format(member)

        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(page)

    @raffler.command(name="end", pass_context=True, no_pm=True)
    async def end_raffle(self, ctx, name: str):
        """end a raffle"""
        server = ctx.message.server
        author = ctx.message.author
        self.init_settings(server)

        name = name.lower()
        if name not in self.raffles[server.id]:
            return await self.bot.say("No such raffle.")
        r = self.raffles[server.id][name]
        if not r.is_author(author):
            return
        if not r.locked:
            return await self.bot.say("You can't end a raffle before drawing  "
                                      "a winner")
        self.raffles[server.id][name].pop(name, None)
        self.save_raffles()
        await self.bot.say("Raffle ended")

    @raffler.command(name="pick", pass_context=True, no_pm=True)
    async def pick_winners(self, ctx, win_count: int, name: str):
        """
        pick a certain number of winners
        if less entered than the possible number of winners,
        everyone wins
        """
        server = ctx.message.server
        author = ctx.message.author
        self.init_settings(server)

        name = name.lower()
        if name not in self.raffles[server.id]:
            return await self.bot.say("No such raffle.")

        r = self.raffles[server.id][name]
        if not r.is_author(author):
            return
        r.locked = True
        entries = r.registered
        members = []
        for e in entries:
            x = server.get_member(e)
            if x is not None:
                members.append(x)

        try:
            winners = random.sample(members, win_count)
        except ValueError:
            winners = members

        output = ""
        if len(winners) == 0:
            output += "No valid winners"
        else:
            if len(winners) == 1:
                output += "The winner is: "
            else:
                output += "The winners are: "
            for winner in winners:
                output += "\n{0.mention}".format(winner)

        for page in pagify(output, delims=["\n", ","]):
            await self.bot.say(page)

        self.save_raffles()

    def is_blacklisted(self, who: Union[discord.Member, discord.Role]):
        if isinstance(who, discord.Role):
            return who.id in self.settings[who.server.id]['blacklisted']
        if isinstance(who, discord.Member):
            if who.id in self.settings[who.server.id]['blacklisted']:
                return True
            for role in who.roles:
                if self.is_blacklisted(role):
                    return True
            return False

    def user_concurrent(self, who: discord.Member):
        server = who.server
        count = 0
        if server.id in self.raffles:
            for name, raffle in self.raffles[server.id].items():
                if raffle.author == who.id:
                    count += 1
        return count


def check_folder():
    f = 'data/raffler'
    if not os.path.exists(f):
        os.makedirs(f)


def check_files():
    f = 'data/raffler/raffles.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})
    f = 'data/raffler/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_files()
    n = Raffler(bot)
    bot.add_cog(n)
