import discord
import asyncio
import re
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import fileIO
from cogs.utils.chat_formatting import *

# This cog is basically a fork of flapjack's ReactPoll
# which itself is basically a fork of the poll function in Red Bot's general.py
# I wanted to use reactpoll while allowing multiple polls in the same channel
# could be a subclass of NewPoll if necessary.
# Full credit is due to Twentysix26 and the Red staff for the original code
# https://github.com/Twentysix26/Red-DiscordBot/blob/develop/cogs/general.py
# As well as to Flapjack who made several improvements to said original
# https://github.com/flapjax/FlapJack-Cogs/blob/master/reactpoll/reactpoll.py


class NewReactPoll():
    # This can be made a subclass of NewPoll()

    def __init__(self, message, text, main):
        self.channel = message.channel
        self.author = message.author.id
        self.client = main.bot
        self.poll_sessions = main.poll_sessions
        msg = [ans.strip() for ans in text.split(";")]
        # Reaction poll supports maximum of 9 answers and minimum of 2
        if len(msg) < 2 or len(msg) > 10:
            self.valid = False
            return None
        else:
            self.valid = True
        self.already_voted = {}
        self.question = msg[0]
        msg.remove(self.question)
        self.answers = {}  # Made this a dict to make my life easier for now
        self.emojis = []
        i = 1
        # Starting codepoint for keycap number emojis (\u0030... == 0)
        base_emoji = [ord('\u0030'), ord('\u20E3')]
        for answer in msg:  # {id : {answer, votes}}
            base_emoji[0] += 1
            self.emojis.append(chr(base_emoji[0]) + chr(base_emoji[1]))
            answer = self.emojis[i-1] + ' ' + answer
            self.answers[i] = {"ANSWER": answer, "VOTES": 0}
            i += 1
        self.message = None

    # Override NewPoll methods for starting and stopping polls
    async def start(self):
        msg = "**POLL STARTED! UID:{} **\n\n{}\n\n".format(self.message.id,
                                                           self.question)
        for id, data in self.answers.items():
            msg += "{}\n".format(data["ANSWER"])
        msg += ("\nSelect the number to vote!")
        self.message = await self.client.send_message(self.channel, msg)
        for emoji in self.emojis:
            await self.client.add_reaction(self.message, emoji)
            await asyncio.sleep(0.5)

    async def endPoll(self):
        self.valid = False
        # Need a fresh message object
        self.message = await self.client.get_message(self.channel,
                                                     self.message.id)
        msg = "**POLL ENDED!**\n\n{}\n\n".format(self.question)
        for reaction in self.message.reactions:
            if reaction.emoji in self.emojis:
                self.answers[ord(reaction.emoji[0])-48]["VOTES"] = \
                    reaction.count - 1
        await self.client.clear_reactions(self.message)
        cur_max = 0  # Track the winning number of votes
        # Double iteration probably not the fastest way, but works for now
        for data in self.answers.values():
            if data["VOTES"] > cur_max:
                cur_max = data["VOTES"]
        for data in self.answers.values():
            if cur_max > 0 and data["VOTES"] == cur_max:
                msg += "**{} - {} votes**\n".format(data["ANSWER"],
                                                    str(data["VOTES"]))
            else:
                msg += "*{}* - {} votes\n".format(data["ANSWER"],
                                                  str(data["VOTES"]))
        await self.client.send_message(self.channel, msg)
        self.poll_sessions.remove(self)


class LongTermPolling:
    """Create polls using emoji reactions"""

    def __init__(self, bot):
        self.bot = bot
        #  self.polls = dataIO.load_json('data/longtermpolling/polls.json')
        #  Todo: implement persistence across bot restarts
        self.poll_sessions = []

    @commands.group(no_pm=True, pass_context=True)
    @checks.mod_or_permissions(manage_messages=True)
    async def ltp(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @ltp.command(pass_context=True, no_pm=True, name="start")
    async def _add_rpoll(self, ctx, *poll):
        """Add a poll
        poll should be in the form of a question, followed by answers
        the question and each answer should be seperated by a semicolon
        """
        message = ctx.message
        channel = message.channel
        server = message.server
        author = message.author

        p = NewReactPoll(message, " ".join(poll), self)
        if p.valid:
            self.poll_sessions.append(p)
            await p.start()
        else:
            await self.bot.send_cmd_help(ctx)

    @ltp.command(pass_context=True, no_pm=True, name="close")
    async def _rem_rpoll(self, ctx, poll_ID: str):
        """closes a poll by the UID of the poll.
        """
        message = ctx.message
        server = message.server

        for channel in server.channels:
            try:
                msg = await self.bot.get_message(channel, poll_ID)
                if msg:
                    p = self.getPollByMessage(message)
                    if p:
                        return await p.endPoll()
                    else:
                        return await self.bot.say("No such poll")
                    break
            except Exception:
                pass

        await self.bot.say("I couldn't find that poll")

    def getPollByMessage(self, message):
        for poll in self.poll_sessions:
            if poll.message.id == message.id:
                return poll
        return False

    async def reaction_listener(self, reaction, user):
        # Listener is required to remove bad reactions
        if user == self.bot.user:
            return  # Don't remove bot's own reactions
        message = reaction.message
        emoji = reaction.emoji
        if self.getPollByMessage(message):
            p = self.getPollByMessage(message)
            if message.id == p.message.id and not reaction.custom_emoji \
                    and emoji in p.emojis:
                # Valid reaction
                if user.id not in p.already_voted:
                    # First vote
                    p.already_voted[user.id] = str(emoji)
                    return
                else:
                    # Allow subsequent vote but remove the previous
                    await self.bot.remove_reaction(message,
                                                   p.already_voted[user.id],
                                                   user)
                    p.already_voted[user.id] = str(emoji)
                    return


def setup(bot):
    n = LongTermPolling(bot)
    bot.add_cog(n)
    bot.add_listener(n.reaction_listener, "on_reaction_add")
