from .core import MacroDice


def setup(bot):
    old_roll = bot.remove_command("roll")
    bot.add_cog(MacroDice(bot, old_roll=old_roll))
