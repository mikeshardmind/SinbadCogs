from .scheduler import Scheduler


def setup(bot):
    bot.add_cog(Scheduler(bot))
