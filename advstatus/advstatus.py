import discord
from discord.ext import commands
from cogs.utils import checks


class AdvStatus:
    """
    boredom
    """

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(name='changepresence', pass_context=True)
    async def changepresence(self, ctx, gametype, *, gamename):
        """
        gametype should be a numeric value based on the below
        'playing'   : 0,
        'listening' : 2,
        'watching' : 3

        To set streaming look at [p]help set stream
        """

        server = ctx.message.server

        current_status = server.me.status if server is not None else None

        if len(gamename.strip()) == 0:
            if current_status is None:
                return await self.bot.say('cant set an empty status')
            else:
                title = current_status
        else:
            title = gamename.strip()

        gt = int(gametype)
        if gt not in [0, 2, 3]:
            return await self.bot.send_cmd_help(ctx)

        game = discord.Game(name=title, type=gt)
        await self.bot.change_presence(game=game, status=current_status)
        await self.bot.say("Done.")


def setup(bot):
    bot.add_cog(AdvStatus(bot))
