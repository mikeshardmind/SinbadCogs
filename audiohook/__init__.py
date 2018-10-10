from .audiohook import AudioHook


def setup(bot):
    bot.add_cog(AudioHook(bot))