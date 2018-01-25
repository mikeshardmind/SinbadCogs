import discord
from discord.ext import commands
from .utils.chat_formatting import pagify
from __main__ import settings


class MentionMods:
    """
    Mention online mods/admins
    use [p]set modrole and [p]set adminrole
    to ensure there are roles which the bot aknowledges
    as mod/admin
    """

    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0001)"

    def __init__(self, bot):
        self.bot = bot

    @commands.cooldown(1, 300, commands.BucketType.server)
    @commands.command(pass_context=True, no_pm=True)
    async def mentionmods(self, ctx):
        """
        mentions online mods and admins
        """
        server = ctx.message.server
        mod_role_name = settings.get_server_mod(server).lower() \
            if settings.get_server_mod(server) else None
        admin_role_name = settings.get_server_admin(server).lower() \
            if settings.get_server_admin(server) else None
        rolenames = [rn for rn in (mod_role_name, admin_role_name) if rn]
        roles = [r for r in server.roles
                 if r.name.lower() in rolenames]
        mentions = [m.mention for m in server.members
                    if not set(m.roles).isdisjoint(roles)
                    and m.status == discord.Status.online]

        output = " ".join(mentions)
        if len(output) == 0:
            return await self.bot.say("No online mods/admins")
 
        for page in pagify(output):
            await self.bot.say(page)


def setup(bot):
    bot.add_cog(MentionMods(bot))
