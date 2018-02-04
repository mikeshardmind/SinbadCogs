import discord
from .utils import checks
from discord.ext import commands
import csv
from pathlib import Path
from datetime import datetime
import os

path = Path('data/membercsv')


class MemberCSV:
    """
    CSV generation of data
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "0.0.1a"

    def __init__(self, bot):
        self.bot = bot

    async def csv_from_guild(self, who: discord.Member) -> Path:
        server = who.server
        fp = path / "{0}-{1.server.id}-{1.id}.csv".format(
            str(datetime.utcnow())[:10], who)
        with open(fp, 'x') as csvfile:
            fieldnames = [
                'id',
                'name',
                'highestrole',
                'membersince',
                'discordmembersince',
                'memberage',
                'lastmessage',
                'currentstatus',
                'currentactivity'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for member in sorted(server.members, key=lambda m: m.joined_at):
                writer.writerow(await self.get_member_row(member))
        return fp

    async def get_member_row(self, member: discord.Member) -> dict:
        ret = {
            'id': member.id,
            'name': str(member),
            'highestrole': "{0.name} ({0.id})".format(member.top_role),
            'membersince': member.joined_at.strftime("%d %b %Y %H:%M"),
            'discordmembersince': member.created_at.strftime("%d %b %Y %H:%M"),
            'memberage': "{} days.".format(
                (datetime.utcnow() - member.joined_at).days),
            'currentstatus': str(member.status)
        }
        if member.game is None:
            g = ""
        elif member.game.type == 0:
            g = "Playing: {}".format(member.game)
        elif member.game.type == 1:
            g = "Streaming: {}  || Streamurl: {}".format(
                member.game, member.game.url)
        elif member.game.type == 2:
            g = "Listening to: {}".format(member.game)
        elif member.game.type == 3:
            g = "Watching: {}".format(member.game)
        ret['currentactivity'] = g

        server = member.server
        msg_time = None
        for channel in filter(
                lambda c: c.type.name == 'text', server.channels):
            try:
                async for message in self.bot.logs_from(
                        channel, limit=10000, reverse=True):
                    if message.author.id == member.id:
                        if msg_time is None:
                            msg_time = message.timestamp
                        else:
                            msg_time = max(msg_time, message.timestamp)
                        break
            except Exception:
                pass

        ret['lastmessage'] = \
            msg_time.strftime("%d %b %Y %H:%M") if msg_time else ""

        return ret

    @commands.command(name='getmembercsv', pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def getmembercsv(self, ctx):
        """
        get a csv with member data
        """

        try:
            await self.bot.whisper(
                "This might take a few minutes depending on server size")
        except Exception:
            return await self.bot.say(
                "I can't do that. I need to be able to message you.")
        try:
            fp = await self.csv_from_guild(ctx.message.author)
        except FileExistsError:
            return await self.bot.say(
                'Be patient, im working on it already.')
        await self.bot.send_file(ctx.message.author, fp)
        os.remove(fp.resolve())


def setup(bot):
    if path.exists:
        path.rmdir()
    path.mkdir(exist_ok=True, parents=True)
    bot.add_cog(MemberCSV(bot))
