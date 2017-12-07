import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from __main__ import settings


class MentionMods:
    """
    Mention online mods/admins
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(1, 300, commands.BucketType.server)
    @commands.command(pass_context=True, no_pm=True)
    async def mentionmods(self, ctx):
        """
        mentions online mods and admins
        """
        server = ctx.message.server
        mod_role_name = settings.get_server_mod(server).lower()
        admin_role_name = settings.get_server_admin(server).lower()
        roles = [r for r in server.roles
                 if r.name.lower() in (admin_role_name, mod_role_name)]
        mentions = [m.mention for m in server.members
                    if not set(m.roles).isdisjoint(roles)
                    and m.status == discord.Status.online]

        output = " ".join(mentions)

        for page in pagify(output):
            await self.bot.say(page)


def setup(bot):
    bot.add_cog(MentionMods(bot))
