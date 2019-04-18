import io
import sys
from copy import copy

import discord
from redbot.core import checks
from redbot.core import commands
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify

_ = Translator("MessageBox", __file__)

_old_contact = None


class MessageBoxError(Exception):
    pass


@cog_i18n(_)
class MessageBox(commands.Cog):
    """
    replace contact with something less obnoxious
    """

    __version__ = "2.0.0"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(output=None)

    def cog_unload(self):
        global _old_contact
        if _old_contact:
            self.bot.remove_command("contact")
            self.bot.add_command(_old_contact)

    @checks.is_owner()
    @commands.command(name="msgboxset")
    async def msgboxset(self, ctx, channel: discord.TextChannel):
        """
        sets the channel where messages should be sent
        """
        await self.config.output.set(channel.id)
        await ctx.tick()

    # more permissive since not DM
    @commands.cooldown(3, 60, commands.BucketType.user)
    @commands.command(name="contact", aliases=["msgbox"])
    async def replacement_contact(self, ctx, *, message: str = ""):
        """
        send a message to the bot owner
        """

        if not message and not ctx.message.attachments:
            raise commands.BadArgument(_("Need a message or attach"))
        try:
            m = copy(ctx.message)
            m.content = message if message else ""
            await self.process_message(ctx.message, m.clean_content)
        except MessageBoxError as e:
            await ctx.send("{}".format(e))
        else:
            await ctx.tick()

    async def process_message(self, message: discord.Message, content: str):
        send_to = discord.utils.get(
            self.bot.get_all_channels(), id=(await self.config.output())
        )
        if send_to is None:
            raise MessageBoxError(_("Hmm.. no channel set up to recieve this"))

        attach = None
        if message.attachments:
            files = []
            size = 0
            max_size = 8 * 1024 * 1024
            for a in message.attachments:
                _fp = io.BytesIO()
                await a.save(_fp)
                size += sys.getsizeof(_fp)
                if size > max_size:
                    await message.channel.send(
                        _(
                            "Could not forward attatchments. "
                            "Total size of attachments in a single "
                            "message must be less than 8MB."
                        )
                    )
                    break
                files.append(discord.File(_fp, filename=a.filename))
            else:
                attach = files

        _content = _("Contact from {0} ({0.id})\n").format(message.author)
        if content:
            _content += content

        for page in pagify(_content):
            await send_to.send(page, files=attach)
            if attach:
                del attach


def setup(bot):
    n = MessageBox(bot)
    global _old_contact
    _old_contact = bot.get_command("contact")
    if _old_contact:
        bot.remove_command(_old_contact.name)
    bot.add_cog(n)
