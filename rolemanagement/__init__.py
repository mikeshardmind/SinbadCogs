from .core import RoleManagement

__end_user_data_statement__ = (
    "This cog does not persistently store end user data. "
    "This cog does store discord IDs as needed for operation. "
)


def setup(bot):
    cog = RoleManagement(bot)
    bot.add_cog(cog)
    cog.init()
