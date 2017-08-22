import os
import asyncio
import discord
import logging
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from discord.utils import find


class FakeQuote:
    """
    Fake quotes
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0"

    def __init__(self, bot):
        self.bot = bot

    @checks.is_owner()
    @commands.command(name="fq", hidden=True, pass_context=True, no_pm=True)
    async def fakequote(self, ctx):
        message = ctx.message
        channel = message.channel
        author = message.author
        await self.bot.delete_message(message)
        dm = await self.bot.send_message(author, "Welcome to the interactive "
                                         "fake quote process.")

        await self.bot.send_message(author, "Give me the name of the channel")

        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=30)
        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")

        cname = response.clean_content.lower()

        await self.bot.send_message(author, "Give me the name of the server")

        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=30)
        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")
        sname = response.clean_content

        await self.bot.send_message(author, "Give me a timestamp format:\n"
                                    "`YYYY-MM-DD HH:MM`")
        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=60)
        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")
        fake_time = response.clean_content

        await self.bot.send_message(author, "Give me the fake message")
        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=120)
        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")

        content = response.clean_content

        await self.bot.send_message(author, "Give me the ID of who I am "
                                    "impersonating")
        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=60)

        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")
        user = await self.bot.get_user_info(response.clean_content)

        avatar = user.avatar_url if user.avatar \
            else user.default_avatar_url
        footer = 'Said in {} #{} at {} UTC'.format(sname, cname, fake_time)
        em = discord.Embed(description=content, color=discord.Color.purple())
        em.set_author(name='{}'.format(user.name), icon_url=avatar)
        em.set_footer(text=footer)

        await self.bot.send_message(author, "Here is the preview: ")
        await self.bot.send_message(author, embed=em)
        await self.bot.send_message(author, "Should I send this? (y/n)")
        response = await self.bot.wait_for_message(channel=dm.channel,
                                                   author=author, timeout=60)

        if response is None:
            return await self.bot.send_message(author, "You took too long "
                                               "Try again when you are ready")

        if response.clean_content.lower() == "y":
            await self.bot.send_message(channel, embed=em)


def setup(bot):
    n = FakeQuote(bot)
    bot.add_cog(n)
