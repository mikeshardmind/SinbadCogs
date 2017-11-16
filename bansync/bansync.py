import asyncio
import discord
from discord.ext import commands
from .utils import checks
from cogs.utils.chat_formatting import box, pagify

path = 'data/bansync'


class BanSync:
    """
    Syncs bans between servers
    """
    __version__ = "1.0.0"
    __author__ = "mikeshardmind (Sinbad#0413)"

    def __init__(self, bot):
        self.bot = bot
        self.modlog = self.bot.get_cog('Mod')

    @checks.is_owner()
    @commands.group(name='bansync', pass_context=True)
    async def bansync(self, ctx, auto: bool=False):
        """
        syncs bans across servers
        """
        servers = []
        if not auto:
            while True:
                s = await self.discover_server(ctx.message.author)
                if s is -1:
                    break
                elif s is None:
                    continue
                else:
                    servers.append(s)
        elif auto is True:
            servers = [s for s in self.bot.servers
                       if s.me.server_permissions.ban_members]

        if len(servers) < 2:
            return await self.bot.whisper('I need at least 2 servers to sync')

        bans = {}

        for server in servers:
            try:
                server_bans = await self.bot.get_bans(server)
            except discord.Forbidden:
                return await self.bot.whisper("I can't do that")
            else:
                bans[server.id] = server_bans

        for server in servers:
            to_ban = []
            for k, v in bans.items():
                to_ban.extend([m for m in v if m not in bans[server.id]])
            for user in to_ban:
                member = server.get_member(user.id)
                if member is not None:
                    try:
                        await self.bot.ban(member, delete_message_days=0)
                    except discord.Forbidden:
                        return await self.bot.whisper("I can't do that")
                    else:
                        if self.modlog:
                            await self.modlog.new_case(
                                server,
                                user=member,
                                action="BAN",
                                reason="ban sync")
                    await asyncio.sleep(1)
                else:
                    try:
                        await self.bot.http.ban(user.id, server.id, 0)
                    except discord.NotFound:
                        pass
                    except discord.Forbidden:
                        return await self.bot.whisper("I can't do that")
                    else:
                        if self.modlog:
                            await self.modlog.new_case(
                                server,
                                action="HACKBAN",
                                user=user,
                                reason="ban sync")

        await self.bot.whisper('bans synced')

    async def discover_server(self, author: discord.User):
        output = ""
        servers = sorted(self.bot.servers, key=lambda s: s.name)
        for i, server in enumerate(servers, 1):
            output += "{}: {}\n".format(i, server.name)
        output += "Select a server to add to the sync list by number, "\
            "or enter \"-1\" to stop adding servers"
        for page in pagify(output, delims=["\n"]):
            dm = await self.bot.send_message(author, box(page))

        message = await self.bot.wait_for_message(channel=dm.channel,
                                                  author=author, timeout=15)
        if message is not None:
            try:
                message = int(message.content.strip())
                if message == -1:
                    return -1
                else:
                    server = servers[message - 1]
            except ValueError:
                await self.bot.send_message(author,
                                            "That wasn't a valid choice")
                return None
            except IndexError:
                await self.bot.send_message(author,
                                            "That wasn't a valid choice")
                return None
            else:
                return server
        else:
            await self.bot.say("You took too long, try again later")
            return None


def setup(bot):
    n = BanSync(bot)
    bot.add_cog(n)
