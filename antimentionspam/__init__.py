from . import antimentionspam


def setup(bot):
    bot.add_cog(antimentionspam.AntiMentionSpam(bot))
