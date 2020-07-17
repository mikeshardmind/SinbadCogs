from typing import Literal, Optional

import discord
from redbot.core import checks, commands
from redbot.core.config import Config
from redbot.core.utils.antispam import AntiSpam

from .checks import has_active_box


class SuggestionBox(commands.Cog):
    """
    A configureable suggestion box cog
    """

    __version__ = "339.1.0"
    __end_user_data_statement__ = (
        "This cog stores data provided to it by command as needed for operation. "
        "As this data is for suggestions to be given from a user to a community, "
        "it is not reasonably considered end user data and will not be deleted."
    )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord", "owner", "user", "user_strict"],
        user_id: int,
    ):
        if requester == "discord":
            # user is deleted, must comply on IDs here...

            data = await self.config.all_members()
            for guild_id, members in data.items():
                if user_id in members:
                    await self.config.member_from_ids(guild_id, user_id).clear()
            await self.config.user_from_id(user_id).clear()

            grp = self.config.custom("SUGGESTION")

            async with grp as data:
                for message_id, suggestion in data.items():
                    if d := suggestion.get("data"):
                        if d.get("author_id", 0) == user_id:
                            d["author_id"] = 0

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(
            boxes=[],
            add_reactions=False,
            reactions=["\N{THUMBS UP SIGN}", "\N{THUMBS DOWN SIGN}"],
            forms={},  # TODO: Interactive forms.
            approval_queues={},
            log_channel=None,
        )
        # for bot suggestions # TODO
        self.config.register_global(
            boxes=[],
            add_reactions=False,
            reactions=["\N{THUMBS UP SIGN}", "\N{THUMBS DOWN SIGN}"],
            forms={},  # TODO: Interactive forms.
            approval_queues={},
        )
        # raw access w/ customforms not implemented here !! # TODO
        self.config.init_custom("SUGGESTION", 1)
        self.config.register_custom("SUGGESTION", data={})

        # Intended access method:  # TODO
        # self.config.custom("APPROVAL_QUEUE", guild_id, queue_name)
        # queue_name is admind defined.
        # self.config.register_custom(
        #     "APPROVAL_QUEUE",
        #     initial_channel=None,  # id
        #     approved_channel=None,  # id
        #     rejection_channel=None,  # optional, id
        #     approval_emoji=None,  # should be the result of `str(emoji_object)`
        #     rejection_emoji=None,  # see ^
        #     minimum_days_to_vote=0,  # minimum days in server
        #     minimum_days_to_suggest=0,  # minimum days in server
        #     stale_suggestion_days=None,
        #     action_on_stale=Action.NOOP,
        #     vote_blacklist=[],  # list of ids, may be member or role
        #     vote_whitelist=[],  # list of ids, may be member or role
        #     # blacklist always applies, whitelist applies if exists.
        #     vote_formula="threshold",  # should be a string in Formulas.AVAILABLE
        #     formula_int=10,  # obviously, configureable.
        # )
        # self.config.register_custom(
        #     "QUEUE_MESSAGE",
        #     source_queue=[],  # List[List[guild_id, queue_name]]
        #     message_id=None,
        #     channel_id=None,
        #     status=State.PENDING,
        #     # for if moved to another channel at vote
        #     moved_message_id=None,
        #     moved_channel_id=None,
        #     votes=[],  # List[List[int, Action]],
        #     # ordered by vote, removing duplicate votes, only storing valid votes
        # )
        self.config.register_member(blocked=False)
        self.config.register_user(blocked=False)
        self.antispam = {}

    @checks.admin_or_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.group(name="suggestionset", aliases=["setsuggestion"])
    async def sset(self, ctx: commands.GuildContext):
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
                return await ctx.send("Channel is already a suggestion box")
            boxes.append(channel.id)

        await ctx.tick()

    @sset.command(name="remove")
    async def sset_rm(self, ctx, *, channel: discord.TextChannel):
        """
        removes a channel as a suggestionbox
        """
        async with self.config.guild(ctx.guild).boxes() as boxes:
            if channel.id not in boxes:
                return await ctx.send("Channel was not ser as a suggestion box")
            boxes.remove(channel.id)

        await ctx.tick()

    @sset.command(name="addreactions")
    async def sset_adds_reactions(self, ctx, option: Optional[bool] = None):
        """
        sets whether to add reactions to each suggestion

        displays current setting without a provided option.

        off = Don't use reactions
        on = Use reactions
        """
        if option is None:
            current = await self.config.guild(ctx.guild).add_reactions()
            command = command = f"`{ctx.clean_prefix}help suggestionset addreactions`"
            if current:
                base = (
                    "I am adding reactions to suggestions."
                    f"\nUse {command} for more information"
                )
            else:
                base = (
                    "I am not adding reactions to suggestions."
                    f"\nUse {command} for more information"
                )

            await ctx.send(base)
            return

        await self.config.guild(ctx.guild).add_reactions.set(option)
        await ctx.tick()

    @has_active_box()
    @commands.guild_only()
    @commands.command()
    async def suggest(
        self,
        ctx: commands.GuildContext,
        channel: Optional[discord.TextChannel] = None,
        *,
        suggestion: str = "",
    ):
        """
        Suggest something.

        Options
        channel : Mention channel to specify which channel to suggest to
        """

        if ctx.guild not in self.antispam:
            self.antispam[ctx.guild] = {}

        if ctx.author not in self.antispam[ctx.guild]:
            self.antispam[ctx.guild][ctx.author] = AntiSpam([])

        if self.antispam[ctx.guild][ctx.author].spammy:
            return await ctx.send("You've sent too many suggestions recently.")

        if not suggestion:
            return await ctx.send("Please try again while including a suggestion.")

        channel = await self.get_suggestion_channel(ctx, channel)
        if not channel:
            return

        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.send_messages and perms.embed_links):
            return await ctx.send("I don't have the required permissions")

        embed = discord.Embed(color=(await ctx.embed_color()), description=suggestion)

        embed.set_author(
            name=f"New suggestion from {ctx.author.display_name} ({ctx.author.id})",
            icon_url=ctx.author.avatar_url,
        )

        try:
            msg = await channel.send(embed=embed)
        except discord.HTTPException:
            return await ctx.send("An unexpected error occured.")
        else:
            grp = self.config.custom("SUGGESTION", msg.id)
            async with grp.data() as data:
                data.update(
                    channel=channel.id, suggestion=suggestion, author=ctx.author.id
                )
            self.antispam[ctx.guild][ctx.author].stamp()
            await ctx.send(f'{ctx.author.mention}: {"Your suggestion has been sent"}')

        if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass

        if await self.config.guild(ctx.guild).add_reactions():

            for reaction in await self.config.guild(ctx.guild).reactions():
                await msg.add_reaction(reaction)

    async def get_suggestion_channel(
        self, ctx: commands.GuildContext, channel: Optional[discord.TextChannel] = None
    ) -> Optional[discord.TextChannel]:
        """ Tries to get the appropriate channel """

        ids = await self.config.guild(ctx.guild).boxes()
        channels = [c for c in ctx.guild.text_channels if c.id in ids]

        if not channel:
            if not channels:
                await ctx.send(
                    "Cannot find channels to send to, even though configured."
                )
                return None

            if len(channels) == 1:
                (channel,) = channels
            else:
                base_error = (
                    "Multiple suggestion boxes available, "
                    "Please try again specifying one of these as the channel:"
                )
                output = f'{base_error}\n{", ".join(c.mention for c in channels)}'
                await ctx.send(output)
                return None

        elif channel not in channels:
            await ctx.send("That channel is not a suggestionbox.")
            return None

        return channel
