import discord
import re

class LinkJoinKiller:
    """
    Auto-ban users joining with invites in name.
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = '0.0.1a'

    def __init__(self):
        self.regex = re.compile(
            r"<?(https?:\/\/)?(www\.)?(discord\.gg|discordapp\.com\/invite)\b([-a-zA-Z0-9/]*)>?"
        )

    async def on_member_join(self, member):
        if not member.guild.me.guild_permissions.ban_members:
            return
        if self.regex.search(str(member)) is not None:
            x = discord.Object(id=member.id)
            await guild.ban(x, reason="invite name")