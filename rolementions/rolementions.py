import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from typing import Union

from .checks import can_mention_here

MemberOrRole = Union[discord.Role, discord.Member]


class RoleMentions(commands.Cog):
    """
    Stuff for mentioning roles.
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.register_role(mentionable_by=[], needs_fix=False)
        self.config.register_channel(mentions_here=False)
        self.config.register_custom(
            "CMENTION", usable_by=[], to_mention=[], template=None
        )  # (guild.id, name) -> data

    @commands.guild_only()
    @commands.group()
    async def rmentionset(self, ctx):
        """
        Configuration settings for RoleMentions
        """
        pass

    @checks.admin_or_permissions(manage_guild=True)
    @rmentionset.command()
    async def mentionableby(
        self,
        ctx: commands.Context,
        role: discord.Role,
        who: commands.Greedy[MemberOrRole] = None,
    ):
        """
        Adds one or more users or roles to the people who can mention a role.
        
        I suggest using an ID or mention of the roles or members for safety,
        but I'm not stopping you from using this unsafely.
        """

        if not who:
            return await ctx.send_help()
