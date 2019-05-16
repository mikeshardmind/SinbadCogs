from redbot.cogs.mod import mod
from typing import Union, Dict, List, cast
from datetime import timedelta

import discord
from redbot.core import commands, checks
from redbot.core.utils.antispam import AntiSpam
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("I am become nihilism, destroyer of meaningful strings", __file__)

antispam_intervals = [
    (timedelta(seconds=5), 3),
    (timedelta(minutes=1), 5),
    (timedelta(hours=1), 30),
]


@cog_i18n(_)
class Mod(mod.Mod):
    """
    I *wanted* to make a new class from the existing one, but compositing in future of mod
    makes that a tad bit more work than I want for this.
    """

    def __init__(self, bot):
        super().__init__(bot)
        self.user_finder_as: Dict[discord.User, AntiSpam] = {}

    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, send_messages=True)
    @commands.command()
    async def finduser(self, ctx, *, user: Union[discord.Member, int]):
        """
        May find a user. Maybe.
        """
        if ctx.author in self.user_finder_as and self.user_finder_as[ctx.author].spammy:
            return
        try:
            _id = user.id  # type: ignore
            user_obj: Union[discord.User, None] = cast(discord.User, user)
        except AttributeError:
            _id = user
            if _id in {m.id for m in self.bot.get_all_members()}:
                user_obj = self.bot.get_user(_id)  # stale cache avoidance
            else:
                user_obj = None

        is_owner = await ctx.bot.is_owner(ctx.author)

        if not is_owner:
            if ctx.author not in self.user_finder_as:
                self.user_finder_as[ctx.author] = AntiSpam(antispam_intervals)
                self.user_finder_as[ctx.author].stamp()
            if user_obj is None:
                return await ctx.send(
                    _("I couldn't locate that user in shared servers")
                )

        guilds: List[discord.Guild] = []
        if user_obj is None and is_owner:
            try:
                try:
                    user_obj = await self.bot.fetch_user(_id)
                except AttributeError:  # 3.0 compat
                    user_obj = await self.bot.get_user_info(_id)
            except discord.NotFound:
                return await ctx.send(_("No such user."))
            except discord.HTTPException:
                return await ctx.send(
                    _("Something unexpected prevented this user from being found.")
                )
        else:
            found_guilds = [g for g in self.bot.guilds if g.get_member(_id)]
            shared_guilds = [g for g in found_guilds if ctx.author in g.members]
            guilds = found_guilds if is_owner else shared_guilds
            if not guilds and not (is_owner and user_obj):  # RHS can happen on user ban
                return await ctx.send(
                    _("I couldn't locate that user in shared servers")
                )

        user_obj = cast(discord.User, user_obj)  # other cases handled above

        since_created = (ctx.message.created_at - user_obj.created_at).days
        user_created = user_obj.created_at.strftime("%d %b %Y %H:%M")
        created_on = _("{}\n({} days ago)").format(user_created, since_created)

        data = discord.Embed(colour=(await ctx.embed_color()))
        data.add_field(name=_("Joined Discord on"), value=created_on)
        name = str(user_obj)
        if user_obj.avatar:
            avatar = user_obj.avatar_url_as(static_format="png")
            data.set_author(name=name, url=avatar)
            data.set_thumbnail(url=avatar)
        else:
            data.set_author(name=name)

        if guilds:
            val = ", ".join((g.name for g in guilds))
            data.add_field(name=_("Servers"), value=val, inline=False)

        await ctx.send(embed=data)

    async def get_names_and_nicks(self, *args, **kwargs):
        # dummy func so userinfo doesnt break
        return [], []

    # leaving this undecorated intentionally
    async def on_member_update(self, *args, **kwargs):
        # kill saving member name changes, also popped during setup.
        pass

    # noinspection PyMethodOverriding
    @property
    def names(self):  # kill now useless command
        return None


Mod.__doc__ = mod.Mod.__doc__  # preserve help
