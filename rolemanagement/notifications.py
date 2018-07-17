import discord
from collections import namedtuple


mockedmember = namedtuple()


class NotificationMixin:


    async def maybe_notify(self, before, after):

        notifychan = await self.config.guild(before.guild).notify_channel()
        if notifychan is None:
            return

        r_after, r, before = set(after.roles), set(before.roles)

        gained = r_after - r_before
        lost = r_before - r_after

        conflicts = []

        for role in gained:
