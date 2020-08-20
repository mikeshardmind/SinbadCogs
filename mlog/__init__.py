from redbot.core.config import Config
from redbot.core.errors import CogLoadError

from .core import MLog

__red_end_user_data_statement__ = (
    "This cog logs messages and does not respect the data APIs. "
    "Bot owners have been warned against loading this cog as it is a work in progress. "
    "Bot owners will receive notice of attempts to delete data and it is on them to handle "
    "this manually at the current time."
)


async def setup(bot):
    notice = Config.get_conf(
        None,
        identifier=-78631113035100160,
        cog_name="Sinbad_Final_Update",
        force_registration=True,
    )
    notice.register_user(notified=False)
    async with notice.get_users_lock():
        notified = await notice.user(bot.user).notified()
        if not notified:
            await bot.send_to_owners(
                "This cog still functions, but I suggest you leave and stop using Red. "
                "I was removed from Red for not wanting my work misrepresented by the "
                "organization, and stating what I would do *if* that continued. "
                'For how much Red and it\'s members go after people who " take credit" '
                "for their work, they sure were quick to dismiss mine. "
                "The cog will recieve no further updates, nor is anyone legally allowed to fork to update."
            )
            await notice.user(bot.user).notified.set(True)
    if bot.user.id != 275047522026913793:
        raise CogLoadError(
            "Hey, stop that. "
            "This was listed as WIP *and* hidden, "
            "*and* warned you about *liabilities.* "
            "Last warning, stop it. Stop trying to "
            "log messages without understanding how badly this can go."
        )
    cog = MLog(bot)
    bot.add_cog(cog)
    cog.init()
