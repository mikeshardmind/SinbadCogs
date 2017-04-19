import discord
from discord.ext import commands
import wikia


class DofusWikia:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='dwiki', pass_context=True)
    async def dofus_wikia(self, ctx, *args):
        """ Dofus Wikia Search """

        channel = ctx.message.channel

        parse = 0
        args = str(args).replace(' ', '+')
        results = None
        send = None

        try:
            wikia.search('Dofus', args, results=2)
            results = wikia.search('Dofus', args, results=2)[0]

        except ValueError:
            await self.bot.say('```css' + '\n' +
                               'Sorry your search returned nothing or is '
                               'invalid. Please try again or visit:'
                               '  ```' + '\n' +
                               'http://dofuswiki.wikia.com/wiki/Dofus_Wiki')

        try:
            results = results.replace("'", '').replace(' ', '_')
            send = 'http://dofuswiki.wikia.com/wiki/' + results

        except AttributeError:
            pass

        try:
            await self.bot.say(send)

        except discord.errors.HTTPException:
            pass


def setup(bot):
    bot.add_cog(DofusWikia(bot))
