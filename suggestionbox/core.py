from typing import Optional

import discord
from redbot.core.config import Config
from redbot.core import commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.antispam import AntiSpam

from .checks import has_active_box

_ = Translator("??", __file__)


@cog_i18n(_)
class SuggestionBox(commands.Cog):
    """
    A configureable suggestion box cog
    """

    __author__ = "mikeshardmind"
    __version__ = "1.0.3b"
    __flavor_text__ = "V2 featues version, more soon."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(boxes=[], forms={})  # for bot suggestions # TODO
        self.config.register_guild(boxes=[], forms={})
        self.config.register_custom("SUGGESTION", data={})  # raw access w/ custom...
        # forms not implemented here !! # TODO
        self.config.register_member(blocked=False)
        self.config.register_user(blocked=False)
        self.antispam = {}

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="suggestionset", aliases=["setsuggestion"])
    async def sset(self, ctx: commands.Context):
        """
        Configuration settings for SuggestionBox
        """
        pass

    @sset.command(name="make")
    async def sset_make(self, ctx, *, channel: discord.TextChannel):
        """
        sets a channel as a suggestionbox
        """
        async with self.config.guild(ctx.guild).boxes() as boxes:
            if channel.id in boxes:
                return await ctx.send(_("Channel is already a suggestion box"))
            boxes.append(channel.id)

        await ctx.tick()

    @sset.command(name="remove")
    async def sset_rm(self, ctx, *, channel: discord.TextChannel):
        """
        removes a channel as a suggestionbox
        """
        async with self.config.guild(ctx.guild).boxes() as boxes:
            if channel.id not in boxes:
                return await ctx.send(_("Channel was not ser as a suggestion box"))
            boxes.remove(channel.id)

        await ctx.tick()

    @has_active_box()
    @commands.guild_only()  # TODO # Change this with additional logic.
    @commands.command()
    async def suggest(
        self,
        ctx,
        channel: Optional[discord.TextChannel] = None,
        *,
        suggestion: str = "",
    ):
        """
        Suggest something.
        """

        if ctx.guild not in self.antispam:
            self.antispam[ctx.guild] = {}

        if ctx.author not in self.antispam[ctx.guild]:
            self.antispam[ctx.guild][ctx.author] = AntiSpam([])

        if self.antispam[ctx.guild][ctx.author].spammy:
            return await ctx.send(_("You've send too many suggestions recently."))

        if channel is None:
            ids = await self.config.guild(ctx.guild).boxes()
            channels = [c for c in ctx.guild.text_channels if c.id in ids]

            if not channels:
                return await ctx.send(
                    _("Cannot find channels to send to, even though configured.")
                )

            if len(channels) == 1:
                channel, = channels
            else:
                base_error = _(
                    "Multiple suggestion boxes available, "
                    "Please try again specifying one of these as the channel:"
                )
                output = f'{base_error}\n{", ".join(c.mention for c in channels)}'
                return await ctx.send(output)

        if not suggestion:
            return await ctx.send(_("Please try again while including a suggestion."))

        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await ctx.send(_("I don't have the required permissions"))

        embed = discord.Embed(color=(await ctx.embed_color()), description=suggestion)

        embed.set_author(
            name=_("New suggestion from {author_info}").format(
                author_info=f"{ctx.author.display_name} ({ctx.author.id})"
            ),
            icon_url=ctx.author.avatar_url,
        )

        try:
            msg = await channel.send(embed=embed)
        except discord.HTTPException:
            return await ctx.send(_("An unexpected error occured."))
        else:
            grp = self.config.custom("SUGGESTION", msg.id)
            async with grp.data() as data:
                data.update(
                    channel=channel.id, suggestion=suggestion, author=ctx.author.id
                )
            self.antispam[ctx.guild][ctx.author].stamp()
            await ctx.send(
                f'{ctx.author.mention}: {_("Your suggestion has been sent")}'
            )

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
