from .core import EconomyTrickle


def setup(bot):
    try:
        assert bot.user.id == 275047522026913793
    except AssertionError:
        raise
    else:
        bot.add_cog(EconomyTrickle(bot))
