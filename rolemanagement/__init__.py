from .core import RoleManagement

import asyncio
from redbot.core import Config


async def maybe_notify(bot):
    """
    I've done this to only notify once,
    and ensure a balance between proper
    user choice and not being a nuisance with it.

    Should 26 follow up with an attempt to prevent this based
    on what I have in my DMs, I'll just remove the check entirely instead
    as I would then value users over the project sanity given
    obvious attempts to hide issues after failing to address them.
    """
    await bot.wait_until_red_ready()
    conf = Config.get_conf(
        None,
        identifier=78631113035100160,
        force_registration=True,
        cog_name="SinbadCogs",
    )
    conf.register_global(has_notified=False)

    async with conf.has_notified.get_lock():
        if await conf.has_notified():
            return
        message = (
            "Hi, Sinbad here."
            "\nI hope you've found my cogs useful, and I hope they remain to be so."
            "\nGiven the reliance some servers have on their functionality, "
            "I'd like to ensure users are aware they are no longer supported by me. "
            "I would suggest you find another solution prior to these breaking, "
            "even if that only entails forking the repository to manage any needed "
            "changes yourself. **I do not anticipate these to break any time soon** "
            "but servers which rely on the functionality within should understand "
            "that the author is no longer involved in maintaining those functionalities."
            "\nMy reasons for this are documented here: "
            "<https://github.com/mikeshardmind/SinbadCogs/blob/v3/why_no_support.md> "
            "\n\nI will not reconsider. I would appreicate if people kept any statements "
            "related to this constructive in nature. While I have left due to this, "
            "it is not beyond possibility that people and the state of things improve. "
            "This information is only provided for making an informed decision, and I "
            "do not condone using it for purposes other than this and improvement "
            "by involved parties."
        )

        await bot.send_to_owners(message)
        await conf.has_notified.set(True)


def setup(bot):
    cog = RoleManagement(bot)
    bot.add_cog(cog)
    cog.init()
    asyncio.create_task(maybe_notify(bot))
