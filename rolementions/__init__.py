from .rolementions import RoleMentions


def setup(bot):
    bot.add_cog(RoleMentions(bot))
