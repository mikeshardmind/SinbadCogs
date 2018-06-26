from .manager import RoleManagement
from .massmanager import MassManager


def setup(bot):
    bot.add_cog(RoleManagement(bot))
    bot.add_cog(MassManager(bot))
