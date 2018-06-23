from .antimentionspam import AntiMentionSpam


def setup(bot):
    bot.add_cog(AntiMentionSpam(bot))