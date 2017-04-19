import discord
from discord.ext import commands
import urllib
import urllib.request
import urllib.parse
import json
import re


cssf = '```css\n{}```'


class Treasure:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='th', pass_context=True)
    async def dofus_th(self, ctx, *args):
        """ Dofus Treasure Hunt Search """

        search = str(args) \
            .replace(' ', '%20') \
            .replace('(', '') \
            .replace("'", '') \
            .replace(')', '') \
            .replace(',', '')

        try:
            urldata = urllib.request.urlopen(
                "https://dofusgo.com/api/pois?clueName=" + search).read(
                ).decode('utf-8')
            urldata = json.loads(urldata)
        except:
            await self.bot.say("Dofusgo.com appears to be down right now.")
        check = 0

        try:
            urldata = urldata[0]
        except IndexError:
            await self.bot.say('```css' + '\n' +
                               'Sorry your search did not return '
                               'anything!  --  '
                               'Please enter it exactly '
                               'how it appears in Dofus!' + '```' + '\n' +
                               'Or visit: https://dofusgo.com/app/clues')
            check = 1

        try:
            urldata = urldata['nameId']
        except TypeError:
            pass

        if check == 0:
            results = "https://dofusgo.com/app/clues/" + str(urldata)

            await self.bot.say("**Search results for: **" +
                               '```css' + '\n' +
                               search.upper().replace("%20", ' ') +
                               "      ----      " +
                               "/* Click the link for more images!" +
                               "      ----    " +
                               "Thanks to Mavvo @ https://dofusgo.com/ "
                               "for the API!*/ " + '```' + '\n' +
                               results + '\n')


def setup(bot):
    bot.add_cog(Treasure(bot))
