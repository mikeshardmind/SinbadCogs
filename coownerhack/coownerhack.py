import discord
from discord.ext import commands
from .utils import checks
import time
from random import randint
from __main__ import settings
from cogs.utils.dataIO import dataIO
import os
import logging

log = logging.getLogger('red.CoownerHack')

DISCLAIMER = "This is a terrible idea. " \
             "Think very carefully before using this. " \
             "If you still want to use it, then go ahead. You were warned. " \
             "Any consequences of the use or misuse of this are on you." \
             "\n\nIf you still want to use this anyway, you can enable it " \
             "by using the hidden command: \n `[pjustfuckmyshitupfam`"


class SanityError(Exception):
    pass


class CoownerHack:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/coownerhack/settings.json')

    def save_json(self):
        dataIO.save_json('data/coownerhack/settings.json', self.settings)

    @checks.is_owner()
    @commands.command(name="justfuckmyshitupfam",
                      pass_context=True, hidden=True)
    async def fuckmyshitup(self, ctx):
        """
        The command name doubles as an extra warning
        """
        self.settings['disclaimer_aknowledged'] = True
        await self.bot.say("Say no more.")

    @checks.is_owner()
    @commands.group(name="setcoownerhack", pass_context=True)
    async def co_owner(self, ctx):
        pass

    @co_owner.command(name="protectcommands", pass_context=True)
    async def protectcommands(self, ctx, *coms: str):
        """
        protect commands from use.
        Multi word commands must be surrounded in quotes
        """
        self.settings['protected_commands'] = \
            self.settings.get('protected_commands', []).extend(coms)
        self.save_json()
        await self.bot.say("k")

    @co_owner.command(name="unprotectcommands", pass_context=True)
    async def unprotectcommands(self, ctx, *coms: str):
        """
        unprotect commands from use.
        Multi word commands must be surrounded in quotes
        """
        for com in coms:
            if com in self.settings['protected_commands']:
                self.settings['protected_commands'] = \
                    self.settings['protected_commands'].remove(com)
        self.save_json()
        await self.bot.say("k")

    @co_owner.command(name="reset", pass_context=True)
    async def co_owner_reset(self, ctx):
        """
        resets to the defaults
        """
        self.settings.pop('protected_commands', None)
        self.settings['users'] = []
        self.settings['disclaimer_aknowledged'] = False
        self.save_json()
        await self.bot.say("Reset")

    @co_owner.command(name="allowuser", pass_context=True)
    async def allow_user(self, ctx, user: discord.Member):
        """allow a user to use commands as owner"""
        if not self.settings['disclaimer_aknowledged']:
            await self._disclaimer()
            return
        if user.id in self.settings['users']:
            return await self.bot.say("Already in list.")
        self.settings['users'].append(user.id)
        self.save_json()
        await self.bot.say("You have only yourself to blame "
                           "if this goes sideways")

    @co_owner.command(name="disallowuser", pass_context=True)
    async def disallow_user(self, ctx, user: discord.Member):
        """remove a user from the allowed list"""
        if not self.settings['disclaimer_aknowledged']:
            await self._disclaimer()
            return
        if user.id not in self.settings['users']:
            return await self.bot.say("Not in list.")
        self.settings['users'].remove(user.id)
        self.save_json()
        await self.bot.say("That's probably for the best")

    @commands.command(name="runasowner", pass_context=True)
    async def run_in_context(self, ctx, *, com: str):
        """
        attempts to run a command as owner.
        """
        try:
            self._sanity_checks(com)
        except SanityError:
            output = "Sanity error encountered: \n" + \
                     "User ID/Name: {0.id}: {0.name}\n" + \
                     "message attempted\n\n: {1.content}" + \
                     "".format(ctx.message.author, ctx.message)
            log.debug(output)
            owner = await self.bot.get_user_info(settings.owner)
            await self.bot.send_message(owner, output)
            return
        else:
            output = "INFO: User ID/Name: {0.id}: {0.name}\n" + \
                     "issued the following as owner: \n" + \
                     "{}".format(com)
            log.debug(output)

        data = \
            {'timestamp': time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime()),
             'content': ctx.prefix + com,
             'channel': ctx.message.channel,
             'channel_id': ctx.message.channel.id,
             'author': {'id': settings.owner},
             'nonce': randint(-2**32, (2**32) - 1),
             'id': randint(10**(17), (10**18) - 1),
             'reactions': []
             }
        message = discord.Message(**data)

        self.bot.dispatch('message', message)

    async def _disclaimer(self):
        if not self.settings['disclaimer_aknowledged']:
            owner = await self.bot.get_user_info(settings.owner)
            await self.bot.send_message(owner, DISCLAIMER)

    def _sanity_checks(self, com: str):
        com = ' '.join(com.split())
        protected_commands = \
            self.settings.get('protected_commands',
                              ["sudo", "setcoownerhack", "debug", "repl"])
        for command in protected_commands:
            if command in com:
                raise SanityError
                return


def check_folder():
    f = 'data/coownerhack'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/coownerhack/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {'users': [], 'disclaimer_aknowledged': False})


def setup(bot):
    check_folder()
    check_file()
    n = CoownerHack(bot)
    bot.add_cog(n)
