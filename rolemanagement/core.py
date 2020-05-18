from __future__ import annotations

import asyncio
import logging
import contextlib
import re
from abc import ABCMeta
from typing import AsyncIterator, Tuple, Optional, Union, List, Dict

import discord
from discord.ext.commands import CogMeta as DPYCogMeta
from redbot.core import checks, commands, bank
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.data_manager import cog_data_path

from .events import EventMixin
from .exceptions import RoleManagementException, PermissionOrHierarchyException
from .massmanager import MassManagementMixin
from .utils import UtilMixin, variation_stripper_re
from .converters import EmojiRolePairConverter


class AddOnceHandler(logging.FileHandler):
    """
    Red's hot reload logic will break my logging if I don't do this.
    """


log = logging.getLogger("red.sinbadcogs.rolemanagement")


for handler in log.handlers:
    # Red hotreload shit.... can't use isinstance, need to check not already added.
    if handler.__class__.__name__ == "AddOnceHandler":
        break
else:
    fp = cog_data_path(raw_name="RoleManagement") / "rolemanagement.log"
    handler = AddOnceHandler(fp)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="%",
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


# This previously used ``(type(commands.Cog), type(ABC))``
# This was changed to be explicit so that mypy
# would be slightly happier about it.
# This does introduce a potential place this
# can break in the future, but this would be an
# Upstream breaking change announced in advance
class CompositeMetaClass(DPYCogMeta, ABCMeta):
    """
    This really only exists because of mypy
    wanting mixins to be individually valid classes.
    """

    pass  # MRO is fine on __new__ with super() use
    # no need to manually ensure both get handled here.


class RoleManagement(
    UtilMixin,
    MassManagementMixin,
    EventMixin,
    commands.Cog,
    metaclass=CompositeMetaClass,
):
    """
    Cog for role management
    """

    # The planned intents changes should only harm this cog if role updates
    # are not handled in the core bot, which would be a massive permission issue.

    __author__ = "mikeshardmind(Sinbad), DiscordLiz"
    __version__ = "330.1.5"

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_global(
            handled_variation=False, handled_full_str_emoji=False
        )
        self.config.register_role(
            exclusive_to=[],
            requires_any=[],
            requires_all=[],
            sticky=False,
            self_removable=False,
            self_role=False,
            protected=False,
            cost=0,
        )
        self.config.register_member(roles=[], forbidden=[])
        self.config.init_custom("REACTROLE", 2)
        self.config.register_custom(
            "REACTROLE", roleid=None, channelid=None, guildid=None
        )  # ID : Message.id, str(React)
        self.config.register_guild(notify_channel=None)
        self._ready = asyncio.Event()
        self._start_task: Optional[asyncio.Task] = None
        super().__init__()

    def cog_unload(self):
        if self._start_task:
            self._start_task.cancel()

    def init(self):
        self._start_task = asyncio.create_task(self.initialization())

        def done_callback(fut: asyncio.Future):

            try:
                fut.exception()
            except asyncio.CancelledError:
                log.info("rolemanagement didn't set up and was cancelled")
            except asyncio.InvalidStateError as exc:
                log.exception(
                    "We somehow have a done callback when not done?", exc_info=exc
                )
            except Exception as exc:
                log.exception("Unexpected exception in rolemanagement: ", exc_info=exc)

        self._start_task.add_done_callback(done_callback)

    async def initialization(self):
        data: Dict[str, Dict[str, Dict[str, Union[int, bool, List[int]]]]]
        await self.bot.wait_until_red_ready()
        if not await self.config.handled_variation():
            data = await self.config.custom("REACTROLE").all()
            to_adjust = {}
            for message_id, emojis_to_data in data.items():
                for emoji_key in emojis_to_data:
                    new_key, c = variation_stripper_re.subn("", emoji_key)
                    if c:
                        to_adjust[(message_id, emoji_key)] = new_key

            for (message_id, emoji_key), new_key in to_adjust.items():
                data[message_id][new_key] = data[message_id][emoji_key]
                data[message_id].pop(emoji_key, None)

            await self.config.custom("REACTROLE").set(data)
            await self.config.handled_variation.set(True)

        if not await self.config.handled_full_str_emoji():
            data = await self.config.custom("REACTROLE").all()
            to_adjust = {}
            pattern = re.compile(r"^(<?a?:)?([A-Za-z0-9_]+):([0-9]+)(\:?>?)$")
            # Am not a fan....
            for message_id, emojis_to_data in data.items():
                for emoji_key in emojis_to_data:
                    new_key, c = pattern.subn(r"\3", emoji_key)
                    if c:
                        to_adjust[(message_id, emoji_key)] = new_key

            for (message_id, emoji_key), new_key in to_adjust.items():
                data[message_id][new_key] = data[message_id][emoji_key]
                data[message_id].pop(emoji_key, None)

            await self.config.custom("REACTROLE").set(data)
            await self.config.handled_full_str_emoji.set(True)

        self._ready.set()

    async def wait_for_ready(self):
        await self._ready.wait()

    async def cog_before_invoke(self, ctx):
        await self.wait_for_ready()
        if ctx.guild:
            await self.maybe_update_guilds(ctx.guild)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.command(name="hackrole")
    async def hackrole(
        self, ctx: commands.GuildContext, user_id: int, *, role: discord.Role
    ):
        """
        Puts a stickyrole on someone not in the server.
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        if not await self.config.role(role).sticky():
            return await ctx.send("This only works on sticky roles.")

        member = ctx.guild.get_member(user_id)
        if member:

            try:
                await self.update_roles_atomically(who=member, give=[role])
            except PermissionOrHierarchyException:
                await ctx.send("Can't, somehow")
            else:
                await ctx.maybe_send_embed("They are in the guild...assigned anyway.")
        else:

            async with self.config.member_from_ids(
                ctx.guild.id, user_id
            ).roles() as sticky:
                if role.id not in sticky:
                    sticky.append(role.id)

            await ctx.tick()

    @checks.is_owner()
    @commands.command(name="rrcleanup", hidden=True)
    async def rolemanagementcleanup(self, ctx: commands.GuildContext):
        """ :eyes: """
        data = await self.config.custom("REACTROLE").all()

        key_data = {}

        for maybe_message_id, maybe_data in data.items():
            try:
                message_id = int(maybe_message_id)
            except ValueError:
                continue

            ex_keys = list(maybe_data.keys())
            if not ex_keys:
                continue

            message = None
            channel_id = maybe_data[ex_keys[0]]["channelid"]
            channel = ctx.bot.get_channel(channel_id)
            if channel:
                with contextlib.suppress(discord.HTTPException):
                    assert isinstance(channel, discord.TextChannel)  # nosec
                    message = await channel.fetch_message(message_id)

            if not message:
                key_data.update({maybe_message_id: ex_keys})

        for mid, keys in key_data.items():
            for k in keys:
                await self.config.custom("REACTROLE", mid, k).clear()

        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="clearmessagebinds")
    async def clear_message_binds(
        self, ctx: commands.Context, channel: discord.TextChannel, message_id: int
    ):
        """
        Clear all binds from a message.
        """
        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.maybe_send_embed("No such message")

        await self.config.custom("REACTROLE", str(message.id)).clear()
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="bulkrolebind")
    async def bulk_role_bind_command(
        self,
        ctx: commands.GuildContext,
        channel: discord.TextChannel,
        message_id: int,
        *,
        emoji_role_pairs: EmojiRolePairConverter,
    ):
        """
        Add role binds to a message.

        Emoji role pairs should be any number of pairs
        of emoji and roles seperated by spaces.
        Role can be specified by ID or name.
        If using a name which includes spaces, enclose in quotes.

        Example usage:

        [p]bulkrolebind
        \N{DIGIT ONE}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}
        "Role One"
        \N{DIGIT TWO}\N{VARIATION SELECTOR-16}\N{COMBINING ENCLOSING KEYCAP}
        Role-two
        """

        pairs = emoji_role_pairs.pairs

        if not await self.all_are_valid_roles(ctx, *pairs.values()):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        try:
            message = await channel.fetch_message(message_id)
        except discord.HTTPException:
            return await ctx.maybe_send_embed("No such message")

        to_store: Dict[str, discord.Role] = {}
        _emoji: Optional[Union[discord.Emoji, str]]

        for emoji, role in pairs.items():

            _emoji = discord.utils.find(lambda e: str(e) == emoji, self.bot.emojis)
            if _emoji is None:
                try:
                    await ctx.message.add_reaction(emoji)
                except discord.HTTPException:
                    return await ctx.maybe_send_embed(f"No such emoji {emoji}")
                else:
                    _emoji = emoji
                    eid = self.strip_variations(emoji)
            else:
                eid = str(_emoji.id)

            if not any(str(r) == emoji for r in message.reactions):
                try:
                    await message.add_reaction(_emoji)
                except discord.HTTPException:
                    return await ctx.maybe_send_embed(
                        "Hmm, that message couldn't be reacted to"
                    )

            to_store[eid] = role

        for eid, role in to_store.items():
            cfg = self.config.custom("REACTROLE", str(message.id), eid)
            await cfg.set(
                {
                    "roleid": role.id,
                    "channelid": message.channel.id,
                    "guildid": role.guild.id,
                }
            )

        await ctx.send(
            f"Remember, the reactions only function according to "
            f"the rules set for the roles using `{ctx.prefix}roleset`",
            delete_after=30,
        )

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="rolebind")
    async def bind_role_to_reactions(
        self,
        ctx: commands.GuildContext,
        role: discord.Role,
        channel: discord.TextChannel,
        msgid: int,
        emoji: str,
    ):
        """
        Binds a role to a reaction on a message...

        The role is only given if the criteria for it are met.
        Make sure you configure the other settings for a role in [p]roleset
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        try:
            message = await channel.fetch_message(msgid)
        except discord.HTTPException:
            return await ctx.maybe_send_embed("No such message")

        _emoji: Optional[Union[discord.Emoji, str]]

        _emoji = discord.utils.find(lambda e: str(e) == emoji, self.bot.emojis)
        if _emoji is None:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.HTTPException:
                return await ctx.maybe_send_embed("No such emoji")
            else:
                _emoji = emoji
                eid = self.strip_variations(emoji)
        else:
            eid = str(_emoji.id)

        if not any(str(r) == emoji for r in message.reactions):
            try:
                await message.add_reaction(_emoji)
            except discord.HTTPException:
                return await ctx.maybe_send_embed(
                    "Hmm, that message couldn't be reacted to"
                )

        cfg = self.config.custom("REACTROLE", str(message.id), eid)
        await cfg.set(
            {
                "roleid": role.id,
                "channelid": message.channel.id,
                "guildid": role.guild.id,
            }
        )
        await ctx.send(
            f"Remember, the reactions only function according to "
            f"the rules set for the roles using `{ctx.prefix}roleset`",
            delete_after=30,
        )

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="roleunbind")
    async def unbind_role_from_reactions(
        self, ctx: commands.Context, role: discord.Role, msgid: int, emoji: str
    ):
        """
        unbinds a role from a reaction on a message
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        await self.config.custom(
            "REACTROLE", f"{msgid}", self.strip_variations(emoji)
        ).clear()
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="roleset", autohelp=True)
    async def rgroup(self, ctx: commands.GuildContext):
        """
        Settings for role requirements
        """
        pass

    @rgroup.command(name="viewreactions")
    async def rg_view_reactions(self, ctx: commands.GuildContext):
        """
        View the reactions enabled for the server
        """
        # This design is intentional for later extention to view this per role

        use_embeds = await ctx.embed_requested()
        react_roles = "\n".join(
            [
                msg
                async for msg in self.build_messages_for_react_roles(
                    *ctx.guild.roles, use_embeds=use_embeds
                )
            ]
        )

        if not react_roles:
            return await ctx.send("No react roles bound here.")

        # ctx.send is already going to escape said mentions if any somehow get generated
        # should also not be possible to do so without willfully being done by an admin.

        color = await ctx.embed_colour() if use_embeds else None

        for page in pagify(
            react_roles, escape_mass_mentions=False, page_length=1800, shorten_by=0
        ):
            # unrolling iterative calling of ctx.maybe_send_embed
            # here to reduce function and coroutine overhead.
            if use_embeds:
                await ctx.send(embed=discord.Embed(description=page, color=color))
            else:
                await ctx.send(page)

    @rgroup.command(name="viewrole")
    async def rg_view_role(self, ctx: commands.GuildContext, *, role: discord.Role):
        """
        Views the current settings for a role
        """

        rsets = await self.config.role(role).all()

        output = (
            f"This role:\n{'is' if rsets['self_role'] else 'is not'} self assignable"
            f"\n{'is' if rsets['self_removable'] else 'is not'} self removable"
            f"\n{'is' if rsets['sticky'] else 'is not'} sticky."
        )
        if rsets["requires_any"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["requires_any"]
            )
            output += f"\nThis role requires any of the following roles: {rstring}"
        if rsets["requires_all"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["requires_all"]
            )
            output += f"\nThis role requires all of the following roles: {rstring}"
        if rsets["exclusive_to"]:
            rstring = ", ".join(
                r.name for r in ctx.guild.roles if r.id in rsets["exclusive_to"]
            )
            output += (
                f"\nThis role is mutually exclusive to the following roles: {rstring}"
            )
        if rsets["cost"]:
            curr = await bank.get_currency_name(ctx.guild)
            cost = rsets["cost"]
            output += f"\nThis role costs {cost} {curr}"
        else:
            output += "\nThis role does not have an associated cost."

        for page in pagify(output):
            await ctx.send(page)

    @rgroup.command(name="cost")
    async def make_purchasable(
        self, ctx: commands.GuildContext, cost: int, *, role: discord.Role
    ):
        """
        Makes a role purchasable for a specified cost.
        Cost must be a number greater than 0.
        A cost of exactly 0 can be used to remove purchasability.

        Purchase eligibility still follows other rules including self assignable.

        Warning: If these roles are bound to a reaction,
        it will be possible to gain these without paying.
        """

        if not await self.all_are_valid_roles(ctx, role):
            return await ctx.maybe_send_embed(
                "Can't do that. Discord role heirarchy applies here."
            )

        if cost < 0:
            return await ctx.send_help()

        await self.config.role(role).cost.set(cost)
        if cost == 0:
            await ctx.send(f"{role.name} is no longer purchasable.")
        else:
            await ctx.send(f"{role.name} is purchasable for {cost}")

    @rgroup.command(name="forbid")
    async def forbid_role(
        self, ctx: commands.GuildContext, role: discord.Role, *, user: discord.Member
    ):
        """
        Forbids a user from gaining a specific role.
        """
        async with self.config.member(user).forbidden() as fb:
            if role.id not in fb:
                fb.append(role.id)
            else:
                await ctx.send("Role was already forbidden")
        await ctx.tick()

    @rgroup.command(name="unforbid")
    async def unforbid_role(
        self, ctx: commands.GuildContext, role: discord.Role, *, user: discord.Member
    ):
        """
        Unforbids a user from gaining a specific role.
        """
        async with self.config.member(user).forbidden() as fb:
            if role.id in fb:
                fb.remove(role.id)
            else:
                await ctx.send("Role was not forbidden")
        await ctx.tick()

    @rgroup.command(name="exclusive")
    async def set_exclusivity(self, ctx: commands.GuildContext, *roles: discord.Role):
        """
        Takes 2 or more roles and sets them as exclusive to eachother
        """

        _roles = set(roles)

        if len(_roles) < 2:
            return await ctx.send("You need to provide at least 2 roles")

        for role in _roles:
            async with self.config.role(role).exclusive_to() as ex_list:
                ex_list.extend(
                    [r.id for r in _roles if r != role and r.id not in ex_list]
                )
        await ctx.tick()

    @rgroup.command(name="unexclusive")
    async def unset_exclusivity(self, ctx: commands.GuildContext, *roles: discord.Role):
        """
        Takes any number of roles, and removes their exclusivity settings
        """

        _roles = set(roles)

        if not _roles:
            return await ctx.send("You need to provide at least a role to do this to")

        for role in _roles:
            ex_list = await self.config.role(role).exclusive_to()
            ex_list = [idx for idx in ex_list if idx not in [r.id for r in _roles]]
            await self.config.role(role).exclusive_to.set(ex_list)
        await ctx.tick()

    @rgroup.command(name="sticky")
    async def setsticky(
        self, ctx: commands.GuildContext, role: discord.Role, sticky: bool = None
    ):
        """
        sets a role as sticky if used without a settings, gets the current ones
        """

        if sticky is None:
            is_sticky = await self.config.role(role).sticky()
            return await ctx.send(
                "{role} {verb} sticky".format(
                    role=role.name, verb=("is" if is_sticky else "is not")
                )
            )

        await self.config.role(role).sticky.set(sticky)
        if sticky:
            for m in role.members:
                async with self.config.member(m).roles() as rids:
                    if role.id not in rids:
                        rids.append(role.id)

        await ctx.tick()

    @rgroup.command(name="requireall")
    async def reqall(
        self, ctx: commands.GuildContext, role: discord.Role, *roles: discord.Role
    ):
        """
        Sets the required roles to gain a role

        Takes a role plus zero or more other roles (as requirements for the first)
        """

        rids = [r.id for r in roles]
        await self.config.role(role).requires_all.set(rids)
        await ctx.tick()

    @rgroup.command(name="requireany")
    async def reqany(
        self, ctx: commands.GuildContext, role: discord.Role, *roles: discord.Role
    ):
        """
        Sets a role to require already having one of another

        Takes a role plus zero or more other roles (as requirements for the first)
        """

        rids = [r.id for r in (roles or [])]
        await self.config.role(role).requires_any.set(rids)
        await ctx.tick()

    @rgroup.command(name="selfrem")
    async def selfrem(
        self, ctx: commands.GuildContext, role: discord.Role, removable: bool = None
    ):
        """
        Sets if a role is self-removable (default False)

        use without a setting to view current
        """

        if removable is None:
            is_removable = await self.config.role(role).self_removable()
            return await ctx.send(
                "{role} {verb} self-removable".format(
                    role=role.name, verb=("is" if is_removable else "is not")
                )
            )

        await self.config.role(role).self_removable.set(removable)
        await ctx.tick()

    @rgroup.command(name="selfadd")
    async def selfadd(
        self, ctx: commands.GuildContext, role: discord.Role, assignable: bool = None
    ):
        """
        Sets if a role is self-assignable via command

        (default False)

        use without a setting to view current
        """

        if assignable is None:
            is_assignable = await self.config.role(role).self_role()
            return await ctx.send(
                "{role} {verb} self-assignable".format(
                    role=role.name, verb=("is" if is_assignable else "is not")
                )
            )

        await self.config.role(role).self_role.set(assignable)
        await ctx.tick()

    @checks.bot_has_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.group(name="srole", autohelp=True)
    async def srole(self, ctx: commands.GuildContext):
        """
        Self assignable role commands
        """
        pass

    @srole.command(name="list")
    async def srole_list(self, ctx: commands.GuildContext):
        """
        Lists the selfroles and any associated costs.
        """

        MYPY = False
        if MYPY:
            # remove this when mypy supports type narrowing from :=
            # It's less efficient, so not removing the actual
            # implementation below
            data: Dict[discord.Role, int] = {}
            for role_id, vals in (await self.config.all_roles()).items():
                role = ctx.guild.get_role(role_id)
                if role and vals["self_role"]:
                    data[role] = vals["cost"]
        else:
            data = {
                role: vals["cost"]
                for role_id, vals in (await self.config.all_roles()).items()
                if (role := ctx.guild.get_role(role_id)) and vals["self_role"]
            }

        if not data:
            return await ctx.send("There aren't any self roles here.")

        # This is really ugly, but relatively optimal.
        # Should this be changed later for clarity instead? --Liz
        message = "\n".join(
            (
                "%s%s" % (role.name, (f": {cost}" if cost else ""))
                for role, cost in sorted(data.items(), key=lambda kv: kv[1])
            )
        )

        for page in pagify(message):
            await ctx.send(box(message))

    @srole.command(name="buy")
    async def srole_buy(self, ctx: commands.GuildContext, *, role: discord.Role):
        """
        Purchase a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
            cost = await self.config.role(role).cost()
        except RoleManagementException:
            return
        except PermissionOrHierarchyException:
            await ctx.send(
                "I cannot assign roles which I can not manage. (Discord Hierarchy)"
            )
        else:
            if not eligible:
                return await ctx.send(
                    f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
                )

            if not cost:
                return await ctx.send(
                    "This role doesn't have a cost. Please try again using `[p]srole add`."
                )

            currency_name = await bank.get_currency_name(ctx.guild)

            try:
                await bank.withdraw_credits(ctx.author, cost)
            except ValueError:
                return await ctx.send(
                    f"You don't have enough {currency_name} (Cost: {cost})"
                )
            else:
                await self.update_roles_atomically(
                    who=ctx.author, give=[role], remove=remove
                )
                await ctx.tick()

    @srole.command(name="add")
    async def sadd(self, ctx: commands.GuildContext, *, role: discord.Role):
        """
        Join a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
            cost = await self.config.role(role).cost()
        except RoleManagementException:
            return
        except PermissionOrHierarchyException:
            await ctx.send(
                "I cannot assign roles which I can not manage. (Discord Hierarchy)"
            )
        else:
            if not eligible:
                await ctx.send(
                    f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
                )

            elif cost:
                await ctx.send(
                    "This role is not free. "
                    "Please use `[p]srole buy` if you would like to purchase it."
                )
            else:
                await self.update_roles_atomically(
                    who=ctx.author, give=[role], remove=remove
                )
                await ctx.tick()

    @srole.command(name="remove")
    async def srem(self, ctx: commands.GuildContext, *, role: discord.Role):
        """
        leave a role
        """
        if await self.config.role(role).self_removable():
            await self.update_roles_atomically(who=ctx.author, remove=[role])
            await ctx.tick()
        else:
            await ctx.send(
                f"You aren't allowed to remove `{role}` from yourself {ctx.author.mention}!`"
            )

    # Stuff for clean interaction with react role entries

    async def build_messages_for_react_roles(
        self, *roles: discord.Role, use_embeds=True
    ) -> AsyncIterator[str]:
        """
        Builds info.

        Info is suitable for passing to embeds if use_embeds is True
        """

        linkfmt = (
            "[message #{message_id}](https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id})"
            if use_embeds
            else "<https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}>"
        )

        for role in roles:
            # pylint: disable=E1133
            async for message_id, emoji_info, data in self.get_react_role_entries(role):

                channel_id = data.get("channelid", None)
                if channel_id:
                    link = linkfmt.format(
                        guild_id=role.guild.id,
                        channel_id=channel_id,
                        message_id=message_id,
                    )
                else:
                    link = (
                        f"unknown message with id {message_id}"
                        f" (use `roleset fixup` to find missing data for this)"
                    )

                emoji: Union[discord.Emoji, str]
                if emoji_info.isdigit():
                    emoji = (
                        discord.utils.get(self.bot.emojis, id=int(emoji_info))
                        or f"A custom enoji with id {emoji_info}"
                    )
                else:
                    emoji = emoji_info

                react_m = f"{role.name} is bound to {emoji} on {link}"
                yield react_m

    async def get_react_role_entries(
        self, role: discord.Role
    ) -> AsyncIterator[Tuple[str, str, dict]]:
        """
        yields:
            str, str, dict

            first str: message id
            second str: emoji id or unicode codepoint
            dict: data from the corresponding:
                config.custom("REACTROLE", messageid, emojiid)
        """

        # self.config.register_custom(
        #    "REACTROLE", roleid=None, channelid=None, guildid=None
        # )  # ID : Message.id, str(React)

        data = await self.config.custom("REACTROLE").all()

        for mid, _outer in data.items():
            if not _outer or not isinstance(_outer, dict):
                continue
            for em, rdata in _outer.items():
                if rdata and rdata["roleid"] == role.id:
                    yield (mid, em, rdata)
