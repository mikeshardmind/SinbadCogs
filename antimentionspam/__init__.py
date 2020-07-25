from .antimentionspam import AntiMentionSpam

__end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users. "
    "Discord IDs of users may occasionaly be logged to file "
    "as part of exception logging."
)


def setup(bot):
    bot.add_cog(AntiMentionSpam(bot))
