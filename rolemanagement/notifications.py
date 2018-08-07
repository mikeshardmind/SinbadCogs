import discord
from collections import namedtuple


RoleMockedMember = namedtuple("RoleMockedMember", ["guild", "roles", "id"])

# stub for later
class NotificationMixin:
    async def maybe_notify(self, before, after):

        notifychan = await self.config.guild(before.guild).notify_channel()
        if notifychan is None:
            return
