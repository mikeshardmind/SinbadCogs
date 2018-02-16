import pathlib
import unicodedata as ud
import re
from cogs.utils import checks
from discord.ext import commands

path = 'data/commandlog'


class CommandLog:
    """
    Debug tool
    """
    __author__ = "mikeshardmind (Sinbad#0413)"
    __version__ = "2.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.cc = self.bot.get_cog('CustomCommands')
        self.unicode_regex = re.compile(r'\\u[a-z0-9%]{4}')

    async def on_command_completion(self, command, ctx):
        msg = (
               '{2.timestamp} (SUCCESS) {0.id} | {0.display_name} in {1.id} | '
               '{1.name} issued: {2.clean_content}'
               ''.format(ctx.message.author, ctx.message.channel, ctx.message))
        self.wr_msg(msg)

    async def on_command_error(self, exc, ctx):
        msg = (
               '{2.timestamp} (FAILURE) {0.id} | {0.display_name} in {1.id} | '
               '{1.name} issued: {2.clean_content} '
               ''.format(ctx.message.author, ctx.message.channel, ctx.message))
        self.wr_msg(msg)

    async def on_message(self, message):
        if self.cc is None:
            return
        if message.channel.is_private:
            return
        if message.channel.server.id in self.cc.c_commands:
            prefix = self.cc.get_prefix(message)
            if not prefix or not self.bot.user_allowed(message):
                return
            cmd = message.content[len(prefix):]
            cmdlist = self.cc.c_commands[message.server.id]
            if cmd in cmdlist or cmd.lower() in cmdlist:
                msg = (
                    '{2.timestamp} (Custom Command) {0.id} | {0.display_name} '
                    'in {1.id} | {1.name} issued: {2.clean_content} '
                    ''.format(message.author, message.channel, message))
            self.wr_msg(msg)

    def wr_msg(self, msg):
        _m = msg.encode('unicode_escape').decode('utf-8')
        ret = ""
        nxt = None
        for match in self.unicode_regex.finditer(_m):
            ret += _m[nxt:match.span()[0]]
            nxt = match.span()[1]
            x = ud.name(
                match.group(0).encode('ASCII').decode('unicode-escape'),
                match.group(0)
            )
            ret += "\\N{" + x + "}"
        with open(path + '/cmds.log', mode='a') as f:
            f.write('\n' + ret)

    @checks.is_owner()
    @commands.command(pass_context=True, name='getcmdlog')
    async def getlog(self, ctx):
        await self.bot.upload(ctx.message.author, path + '/cmds.log')


def setup(bot):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    bot.add_cog(CommandLog(bot))
