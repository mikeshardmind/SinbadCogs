from typing import AsyncIterator, Tuple
import discord
from redbot.core import checks, commands
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify

from .utils import UtilMixin
from .massmanager import MassManagementMixin
from .events import EventMixin

# from .notifications import NotificationMixin
from .exceptions import RoleManagementException, PermissionOrHierarchyException


class RoleManagement(UtilMixin, MassManagementMixin, EventMixin, commands.Cog):
    """
    Cog for role management
    """

    __author__ = "mikeshardmind (Sinbad)"
    __version__ = "3.2.13"
    __flavor_text__ = "Even more feedback."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_role(
            exclusive_to=[],
            requires_any=[],
            requires_all=[],
            sticky=False,
            self_removable=False,
            self_role=False,
            protected=False,
        )
        self.config.register_member(roles=[], forbidden=[])
        self.config.register_custom(
            "REACTROLE", roleid=None, channelid=None, guildid=None
        )  # ID : Message.id, str(React)
        self.config.register_guild(notify_channel=None)
        super().__init__()

    async def __before_invoke(self, ctx):
        if ctx.guild:
            await self.maybe_update_guilds(ctx.guild)

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.command(name="rolebind")
    async def bind_role_to_reactions(
        self,
        ctx: commands.Context,
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

        message = await channel.get_message(msgid)
        if not message:
            return await ctx.maybe_send_embed("No such message")

        _emoji = discord.utils.find(lambda e: str(e) == emoji, self.bot.emojis)
        if _emoji is None:
            try:
                await ctx.message.add_reaction(emoji)
            except discord.DiscordException:
                return await ctx.maybe_send_embed("No such emoji")
            else:
                _emoji = emoji
                eid = emoji
        else:
            eid = _emoji.id

        if not any(str(r) == emoji for r in message.reactions):
            try:
                await message.add_reaction(_emoji)
            except discord.DiscordException:
                return await ctx.maybe_send_embed(
                    "Hmm, that message couldn't be reacted to"
                )

        cfg = self.config.custom("REACTROLE", message.id, eid)
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

        # noinspection PyTypeChecker  # TODO: PR to red to change the type here to a protocol
        cfg = self.config.custom("REACTROLE", msgid)
        async with cfg() as cfg:
            cfg.pop(str(emoji), None)
        await ctx.tick()

    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="roleset", autohelp=True)
    async def rgroup(self, ctx: commands.Context):
        """
        Settings for role requirements
        """
        pass

    @rgroup.command(name="viewreactions")
    async def rg_view_reactions(self, ctx: commands.Context):
        """
        View the reactions enabled for the server
        """
        # This design is intentional for later extention to view this per role

        use_embeds = await ctx.embed_requested()
        # pylint: disable=E1133
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

        color = None

        for page in pagify(
            react_roles, escape_mass_mentions=False, page_length=1800, shorten_by=0
        ):
            # unrolling iterative calling of ctx.maybe_send_embed
            # here to reduce function and coroutine overhead.
            if use_embeds:
                color = color or await ctx.embed_colour()
                await ctx.send(embed=discord.Embed(description=page, color=color))
            else:
                await ctx.send(page)

    @rgroup.command(name="viewrole")
    async def rg_view_role(self, ctx: commands.Context, *, role: discord.Role):
        """
        Views the current settings for a role
        """

        rsets = await self.config.role(role).all()

        output = (
            f"This role:\n{'is' if rsets['self_role'] else 'is not'} self assignable"
            f"\n{'is' if rsets['self_removable'] else 'is not'} self removable"
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

        for page in pagify(output):
            await ctx.send(page)

    @rgroup.command(name="forbid")
    async def forbid_role(
        self, ctx: commands.Context, role: discord.Role, *, user: discord.Member
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
        self, ctx: commands.Context, role: discord.Role, *, user: discord.Member
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
    async def set_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
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
    async def unset_exclusivity(self, ctx: commands.Context, *roles: discord.Role):
        """
        Takes any number of roles, and removes their exclusivity settings
        """

        _roles = set(roles)

        if len(roles) < 1:
            return await ctx.send("You need to provide at least a role to do this to")

        for role in _roles:
            ex_list = await self.config.role(role).exclusive_to()
            ex_list = [idx for idx in ex_list if idx not in [r.id for r in _roles]]
            await self.config.role(role).exclusive_to.set(ex_list)
        await ctx.tick()

    @rgroup.command(name="sticky")
    async def setsticky(self, ctx, role: discord.Role, sticky: bool = None):
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
        self, ctx: commands.Context, role: discord.Role, *roles: discord.Role
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
        self, ctx: commands.Context, role: discord.Role, *roles: discord.Role
    ):
        """
        Sets a role to require already having one of another

        Takes a role plus zero or more other roles (as requirements for the first)
        """

        rids = [r.id for r in (roles or [])]
        await self.config.role(role).requires_any.set(rids)
        await ctx.tick()

    @rgroup.command(name="selfrem")
    async def selfrem(self, ctx, role: discord.Role, removable: bool = None):
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
    async def selfadd(self, ctx, role: discord.Role, assignable: bool = None):
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
    async def srole(self, ctx: commands.Context):
        """
        Self assignable role commands
        """
        pass

    @srole.command(name="add")
    async def sadd(self, ctx: commands.Context, *, role: discord.Role):
        """
        Join a role
        """
        try:
            remove = await self.is_self_assign_eligible(ctx.author, role)
            eligible = await self.config.role(role).self_role()
        except RoleManagementException:
            pass
        except PermissionOrHierarchyException:
            return await ctx.send(
                "I cannot assign roles which I can not manage. (Discord Hierarchy)"
            )
        else:
            if eligible:
                await self.update_roles_atomically(
                    who=ctx.author, give=[role], remove=remove
                )
                return await ctx.tick()

        await ctx.send(
            f"You aren't allowed to add `{role}` to yourself {ctx.author.mention}!"
        )

    @srole.command(name="remove")
    async def srem(self, ctx: commands.Context, *, role: discord.Role):
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

    # migration / update tools

    @rgroup.command(name="fixup", hidden=True)
    async def fixup(self, ctx: commands.Context):
        """
        Removes bad settings, finds extra info as required.
        """
        async with ctx.typing():
            await self.handle_fixup(ctx.guild)
        await ctx.tick()

    @checks.is_owner()
    @rgroup.command("fixupall", hidden=True)
    async def fixupall(self, ctx: commands.Context):
        """
        Removes bad settings, finds extra info as required.
        """
        async with ctx.typing():
            await self.handle_fixup(*self.bot.guilds, checking_all=True)
        await ctx.tick()

    async def handle_fixup(self, *guilds: discord.Guild, checking_all=False) -> None:

        needed_perms = discord.Permissions()
        needed_perms.update(read_messages=True, read_message_history=True)
        roles = {}
        channels = {}
        data = await self.config._get_base_group("REACTROLE").all()
        # str(messageid) -> str(emoji or emojiid) -> actual data

        for guild in guilds:
            roles.update({r.id: r for r in guild.roles})
            channels.update({c.id: c for c in guild.text_channels})

        for mid, _outer in data.items():
            if not isinstance(_outer, dict):
                continue
            if not _outer:
                # can have an empty dict here
                await self.config.custom("REACTROLE", mid).clear()
                continue

            for em, rdata in _outer.items():
                if not rdata:
                    # can have an empty dict here
                    await self.config.custom("REACTROLE", mid, em).clear()
                    continue
                role = roles.get(rdata["roleid"], None)
                if not role:
                    if checking_all:
                        await self.config.custom("REACTROLE", mid, em).clear()
                    continue

                gid = rdata.get("guildid", None)
                if not gid:
                    await self.config.custom("REACTROLE", mid, em).guildid.set(
                        role.guild.id
                    )

                cid = rdata.get("channelid", None)
                if not cid:
                    non_forbidden_encountered = False
                    for channel in role.guild.text_channels:
                        non_forbidden_encountered = False
                        if channel.permissions_for(role.guild.me) >= needed_perms:
                            try:
                                _msg = await channel.get_message(mid)
                            except discord.Forbidden:
                                continue
                            except discord.HTTPException:
                                non_forbidden_encountered = True
                            else:
                                if _msg:
                                    await self.config.custom(
                                        "REACTROLE", mid, em
                                    ).channelid.set(channel.id)
                                    break
                    else:
                        if not non_forbidden_encountered:
                            await self.config.custom("REACTROLE", mid).clear()

    # Stuff for clean interaction with react role entries

    async def build_messages_for_react_roles(
        self, *roles: discord.Role, use_embeds=True
    ) -> AsyncIterator[str]:
        """
        Builds info.

        Info is suitable for passing to embeds if use_embeds is True 
        """

        linkfmt = (
            "[message](https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id})"
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

                if emoji_info.isdigit():
                    emoji = discord.utils.get(self.bot.emojis, id=int(emoji_info))
                    emoji = emoji or f"A custom enoji with id {emoji_info}"
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

        data = await self.config._get_base_group("REACTROLE").all()

        for mid, _outer in data.items():
            if not _outer or not isinstance(_outer, dict):
                continue
            for em, rdata in _outer.items():
                if rdata and rdata["roleid"] == role.id:
                    yield (mid, em, rdata)
