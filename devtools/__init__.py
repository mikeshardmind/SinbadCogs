from . import core
from .patches import patch_bot, remove_patches
from .runner import Runner

__red_end_user_data_statement__ = (
    "This cog does not persistently store data or metadata about users."
)


async def setup(bot):
    await bot.send_to_owners(
        "This cog still functions, but I suggest you leave and stop using Red. "
        "I was removed from Red for not wanting my work misrepresented by the "
        "organization, and stating what I would do *if* that continued. "
        'For how much Red and it\'s members go after people who " take credit" '
        "for their work, they sure were quick to dismiss mine. "
        "The cog will recieve no further updates, nor is anyone legally allowed to fork to update."
    )
    bot.add_cog(core.DevTools(bot))
    bot.add_cog(Runner(bot))
    patch_bot(bot)


def teardown(bot):
    remove_patches(bot)
