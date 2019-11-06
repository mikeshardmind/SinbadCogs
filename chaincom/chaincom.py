import contextlib
from copy import deepcopy

import discord
from redbot.core import commands


def make_fake(original: discord.Message, new_content: str) -> discord.Message:
    data = {}
    data["id"] = discord.utils.time_snowflake(original.created_at)
    data["attachments"] = []
    data["reactions"] = []
    data["attachments"] = []
    data["embeds"] = []
    data["edited_timestamp"] = None
    data["type"] = 0
    data["author"] = {"id": original.author.id}
    data["pinned"] = False
    data["mention_everyone"] = False
    data["tts"] = False
    data["content"] = new_content
    return discord.Message(state=original._state, channel=original.channel, data=data)


class ChainCom(commands.Cog):
    """ Unsupported way to invoke multiple commands in a single message """

    @commands.command()
    async def chaincom(self, ctx, *, coms: str):
        """
        Will absolutely break on commands that try to interact with the message object

        coms: `|` seperated commands without prefix
        """
        commands = coms.split("|")
        for command in commands:
            nc = f"{ctx.prefix}{command.strip()}"
            with contextlib.suppress(Exception):
                await ctx.bot.process_commands(make_fake(ctx.message, nc))
