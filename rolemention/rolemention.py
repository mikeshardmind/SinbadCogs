import discord
from discord.ext import commands
from cogs.utils.chat_formatting import pagify
from cogs.utils import checks


class RoleMention:
    """
    Use this in place of actual role mentions because discord's
    role mention permissions are lacking
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "1.0.0a"

    def __init__(self, bot):
        self.bot = bot

    @checks.mod_or_permissions(manage_message=True)
    @commands.command(name="rolemention", pass_context=True, no_pm=True)
    async def rlmention(self, ctx, *roles: discord.Role):
        """
        mentions all of the users who are a part of
        at least one of the roles

        Will not mention by @ everyone, requires being a mod or
        the ability to manage messages

        You really should only use this on roles people opt into,
        but I'm also not going to try and enforce that. Use this responsibly.
        It's not my problem if you don't.
        """

        _roles = set(r for r in roles if not r.is_everyone)
        if len(_roles) == 0:
            return await self.bot.say(
                "Hmm, you either didn't give me any roles, "
                "or all of the roles you gave "
                "me are not eligible for "
                "this command."
            )

        mentions = [
            m.mention for m in ctx.message.server.members
            if not _roles.isdisjoint(m.roles)
        ]

        mention_str = (
            "Mass mention authorized by {} for members in "
            "one or more of the following roles: {}\n\n"
        ).format(ctx.message.author.mention, ", ".join(r.name for r in _roles))

        mention_str += " ".join(mentions)

        for page in pagify(mention_str, delims=["\n", " "]):
            await self.bot.say(page)


def setup(bot):
    bot.add_cog(RoleMention(bot))
