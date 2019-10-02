from . import sanctuary


def setup(bot):
    bot.add_cog(sanctuary.Sanctuary(bot))
