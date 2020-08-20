from redbot.core.config import Config

from .core import GuildJoinRestrict

__red_end_user_data_statement__ = (
    "This cog persistently stores the minimum "
    "amount of data needed to restrict guild joins to those allowed by settings. "
    "It will not respect data deletion by end users, nor can end users request "
    "their data from this cog since it only stores "
    "discord IDs and whether those IDs are allowed or denied. "
    "Discord IDs may occasionally be logged to a file as needed for audit purposes."
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
    cog = GuildJoinRestrict(bot)
    bot.add_cog(cog)
    cog.init()
