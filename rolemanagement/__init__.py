from .core import RoleManagement


def setup(bot):
    cog = RoleManagement(bot)
    bot.add_cog(cog)
    cog.init()
