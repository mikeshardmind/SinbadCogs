import discord
from discord.ext import commands
from cogs.utils import checks
from discord.utils import snowflake_time

class SinbadUtils:
    """personal utils"""

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(pass_context=True, no_pm=True)
    async def userinfobyid(self, ctx, uid: str):
        """Shows users's information"""
        server = ctx.message.server
        user = server.get_member(uid)
        user_created = snowflake_time(uid).strftime("%d %b %Y %H:%M")
        if user is not None:
            desc = "Is a member of this server"
            col = user.color
            name = "{0.name} #{0.discriminator}".format(user)
            if user.nick is not None:
                name += " AKA: {0.nick}".format(user)
        else:
            user = await self.bot.get_user_info(uid)
            if user is None:
                return await self.bot.say("No such user")
            col = discord.Color.purple
            desc = "Not a member of this server"
            name = "{0.name} #{0.discriminator}".format(user)

        data = discord.Embed(description=desc, colour=col)
        if user.avatar_url:
            data.set_author(name=name, url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)
        else:
            data.set_author(name=name)

        try:
            await self.bot.say(embed=data)
        except Exception:
            pass


def setup(bot):
    n = SinbadUtils(bot)
    bot.add_cog(n)
