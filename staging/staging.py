from typing import Union
from redbot.core import commands, checks
from redbot.core.utils.antispam import AntiSpam
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("I am become nihilism, destroyer of meaningful strings", __file__)

@cog_i18n(_)
class Staging(commands.Cog):
    """
    Collection of things being tested.
    """

    def __init__(self, bot):
        self.bot = bot
        self.user_finder_as = {}

    @commands.command()
    async def finduser(self, ctx, *, user: Union[discord.Member, int] = None):
        """
        May find a user.
        """
        pass  # do this later
        

    