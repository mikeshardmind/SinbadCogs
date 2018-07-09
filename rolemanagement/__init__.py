from .manager import RoleManagement


def setup(bot):
    bot.add_cog(RoleManagement(bot))
