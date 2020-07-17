from __future__ import annotations

import asyncio
import contextlib
from typing import Set

import discord
from redbot.core import checks, commands
from redbot.core.config import Config

from .converters import CogOrCOmmand, CommandConverter, TrinaryBool

# TODO
# user facing terminology has been updated to `allowlist` and `blocklist`
# when more time is available, create a migration for the storage component of this


class ChannelRedirect(commands.Cog):
    """
    Redirect commands from wrong channels
    """

    __version__ = "339.1.0"
    __end_user_data_statement__ = (
        "This cog does not persistently store data or metadata about users."
    )

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(
            mode=None,
            blacklist=[],
            whitelist=[],
            command={},
            cog={},
            immunities={},
            com_whitelist={"cog": {}, "command": {}},
        )

    def cog_unload(self):
        self.bot.remove_before_invoke_hook(self.before_invoke_hook)

    @staticmethod
    def should_early_exit(conf: dict, com: commands.Command):
        if conf["mode"] is None:
            return True

        with contextlib.suppress(KeyError):
            if conf["com_whitelist"]["command"][com.qualified_name]:
                return True
        with contextlib.suppress(KeyError):
            if conf["com_whitelist"]["cog"][com.cog_name]:
                return True

    async def get_allowed_channels(
        self,
        ctx: commands.Context,
        *,
        ignore_overides: bool = False,
        com: commands.Command = None,
    ) -> Set[discord.TextChannel]:

        guild = ctx.guild
        assert guild is not None  # nosec
        com = com or ctx.command
        gset = await self.config.guild(guild).all()
        channels = guild.text_channels
        allowed_ids: Set[int] = set()

        if com and self.should_early_exit(gset, com):
            return set(channels)

        if gset["mode"] == "whitelist":
            allowed_ids = {int(idx) for idx in gset["whitelist"]}

        elif gset["mode"] == "blacklist":
            disallowed_ids = {int(idx) for idx in gset["blacklist"]}
            allowed_ids = {c.id for c in channels} - disallowed_ids

        if not ignore_overides:
            com_extras = gset["command"].get(com.qualified_name, {})
            cog_extras = gset["cog"].get(com.cog_name, {})
            for rule_set in (cog_extras, com_extras):
                for channel_id, allowed in rule_set.items():
                    if allowed:
                        allowed_ids.add(int(channel_id))
                    elif allowed is False:  # trinary
                        allowed_ids.discard(int(channel_id))

        allowed_chans = {channel for channel in channels if channel.id in allowed_ids}

        return allowed_chans

    async def is_redirect_immune(self, ctx):
        if (
            ctx.guild is None
            or ctx.guild.owner == ctx.author
            or await ctx.bot.is_owner(ctx.author)
            or await ctx.bot.is_admin(ctx.author)
        ):
            return True

        imset = await self.config.guild(ctx.guild).immunities.all()
        vals = [v for k, v in imset.items() if k in (str(ctx.channel.id), "global")]
        immune_ids = set()
        for val in vals:
            immune_ids.update({int(v) for v in val})

        if immune_ids & {r.id for r in ctx.author.roles}:
            return True

    async def before_invoke_hook(self, ctx: commands.Context):

        if await self.is_redirect_immune(ctx):
            return True

        allowed_chans = await self.get_allowed_channels(ctx)

        if ctx.channel not in allowed_chans and not isinstance(
            ctx.command, commands.commands._AlwaysAvailableCommand
        ):
            chan_mentions = ", ".join(c.mention for c in allowed_chans)
            await ctx.send(
                f"{ctx.author.mention} This command is only available in {chan_mentions}",
                delete_after=30,
            )
            raise commands.CheckFailure()
        else:
            return True

    @commands.guild_only()
    @checks.admin_or_permissions(manage_guild=True)
    @commands.group(name="redirectset")
    async def rset(self, ctx):
        """
        Setting for channel redirection.
        """
        pass

    @rset.command(name="showsettings")
    async def rest_show_settings(self, ctx, command: CommandConverter = None):
        """
        Shows guild settings, or if a command is provided, the channels that
        command is allowed including exceptions.
        """
        com_obj = command.com if command is not None else None
        channels = await self.get_allowed_channels(
            ctx, com=com_obj, ignore_overides=(command is None)
        )
        msg = "Usable channels:\n" + ", ".join(c.mention for c in channels)
        await ctx.send(msg)

    @rset.command(name="mode")
    async def rset_set_mode(self, ctx, *, mode: str = ""):
        """
        Whether to operate on a allowlist, or a blocklist.
        """

        mode = mode.casefold()
        lookup = {"allowlist": "whitelist", "blocklist": "blacklist"}

        if to_store := lookup.get(mode, None):
            await self.config.guild(ctx.guild).mode.set(to_store)
            await ctx.tick()
        else:
            return await ctx.send_help()

    @rset.command(name="addchan")
    async def rset_add_chan(self, ctx, *channels: discord.TextChannel):
        """
        Adds one or more channels to the current mode's settings.
        """

        if not channels:
            return await ctx.send_help()

        gsets = await self.config.guild(ctx.guild).all()
        mode = gsets["mode"]
        if not mode:
            return await ctx.send(
                "You need to set a mode using `{ctx.prefix}redirectset mode` first".format(
                    ctx=ctx
                )
            )

        for channel in channels:
            if channel.id not in gsets[mode]:
                gsets[mode].append(channel.id)

        await self.config.guild(ctx.guild).set_raw(mode, value=gsets[mode])
        await ctx.tick()

    @rset.command(name="remchan")
    async def rset_rem_chan(self, ctx, *channels: discord.TextChannel):
        """
        Removes one or more channels from the current mode's settings.
        """

        if not channels:
            return await ctx.send_help()

        gsets = await self.config.guild(ctx.guild).all()
        mode = gsets["mode"]
        if not mode:
            return await ctx.send(
                "You need to set a mode using `{ctx.prefix}redirectset mode` first".format(
                    ctx=ctx
                )
            )

        for channel in channels:
            while channel.id in gsets[mode]:
                gsets[mode].remove(channel.id)

        await self.config.guild(ctx.guild).set_raw(mode, value=gsets[mode])
        await ctx.tick()

    @rset.group(name="exceptions")
    async def rset_except(self, ctx):
        """
        Commands for configuring exceptions.
        """
        pass

    @rset_except.command(name="allowcommandeverywhere")
    async def rset_whitelistcom_add(
        self, ctx: commands.Context, *, cog_or_command: CogOrCOmmand
    ):
        """
        Creates an exception allowing a command for all channels.

            May not work with subcommands with parent commands locked!!
        """
        await self.config.guild(ctx.guild).com_whitelist.set_raw(
            *cog_or_command, value=True
        )
        await ctx.tick()

    @rset_except.command(name="unallowcommandeverywhere")
    async def rset_whitelistcom_rem(
        self, ctx: commands.Context, *, cog_or_command: CogOrCOmmand
    ):
        """
        Removes an exception allowing a command in all channels.

        Note: This command name is not a typo as it is undoing

        [p]allowcommandeverywhere

        However, if you have a better name
        feel free to open an issue suggesting it
        """
        await self.config.guild(ctx.guild).com_whitelist.set_raw(
            *cog_or_command, value=False
        )
        await ctx.tick()

    @rset_except.command(name="add")
    async def rset_except_add(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel,
        value: TrinaryBool,
        *,
        cog_or_command: CogOrCOmmand,
    ):
        """
        Creates an exception for a specifc channel/command combination

        value should be one of "allow", "deny", "clear" (to clear an existing setting)

        example: Allow audio cog in music-room even if other settings would deny
            [p]redirectset exceptions add #music-room allow Audio
        """
        await self.config.guild(ctx.guild).set_raw(
            *cog_or_command, str(channel.id), value=value.state
        )
        await ctx.tick()

    @rset_except.command(name="clearall")
    async def reset_except_clear(self, ctx):
        """
        Clears all exceptions.
        """
        reacts = {
            "\N{WHITE HEAVY CHECK MARK}": True,
            "\N{NEGATIVE SQUARED CROSS MARK}": False,
        }
        m = await ctx.send("Are you sure?")
        for r in reacts.keys():
            await m.add_reaction(r)
        try:
            reaction, _user = await self.bot.wait_for(
                "reaction_add",
                check=lambda rr, u: u == ctx.author and str(rr) in reacts,
                timeout=30,
            )
        except asyncio.TimeoutError:
            return await ctx.send("Ok, try responding with an emoji next time.")

        if reacts.get(str(reaction)):
            await self.config.guild(ctx.guild).command.set({})
            await self.config.guild(ctx.guild).cog.set({})
            await ctx.tick()
        else:
            await ctx.send("Okay, keeping the current exceptions")

    @rset.group(name="immune")
    async def rset_immune(self, ctx):
        """
        Settings for roles to be immune from the redirect.
        """
        pass

    @rset_immune.group(name="channel")
    async def rset_chanimmune(self, ctx):
        """
        Channel specific immunities.
        """
        pass

    @rset_chanimmune.command(name="addroles")
    async def rsetchanimmune_addroles(
        self, ctx, channel: discord.TextChannel, *roles: discord.Role
    ):
        """
        Adds roles to redirect immunity.
        """
        if not roles:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).immunities() as ims:
            rids = set(ims.get(str(channel.id), []))
            rids |= {r.id for r in roles}
            to_update = {str(channel.id): list(rids)}
            ims.update(to_update)
        await ctx.tick()

    @rset_chanimmune.command(name="remroles")
    async def rset_chanimmune_remroles(
        self, ctx, channel: discord.TextChannel, *roles: discord.Role
    ):
        """
        Removes roles from redirect immunity.
        """
        if not roles:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).immunities() as ims:
            rids = set(ims.get(str(channel.id), []))
            rids -= {r.id for r in roles}
            to_update = {str(channel.id): list(rids)}
            ims.update(to_update)
        await ctx.tick()

    @rset_immune.group(name="global")
    async def rset_globimmune(self, ctx):
        """
        Global immunities.
        """
        pass

    @rset_globimmune.command(name="addroles")
    async def rset_globimmune_addroles(self, ctx, *roles: discord.Role):
        """
        Adds roles to redirect immunity.
        """
        if not roles:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).immunities() as ims:
            rids = set(ims.get("global", []))
            rids |= {r.id for r in roles}
            to_update = {"global": list(rids)}
            ims.update(to_update)
        await ctx.tick()

    @rset_globimmune.command(name="remroles")
    async def rset_globimmune_remroles(self, ctx, *roles: discord.Role):
        """
        Removes roles from redirect immunity.
        """
        if not roles:
            return await ctx.send_help()
        async with self.config.guild(ctx.guild).immunities() as ims:
            rids = set(ims.get("global", []))
            rids -= {r.id for r in roles}
            to_update = {"global": list(rids)}
            ims.update(to_update)
        await ctx.tick()

    @rset_immune.command(name="list")
    async def rset_list_immune(self, ctx, channel: discord.TextChannel = None):
        """
        Show the immunity settings.

        Either the global ones, or if a channel is provided, the channel ones.
        """

        ims = await self.config.guild(ctx.guild).immunities.all()

        key = str(channel.id) if channel else "global"

        immune_ids = ims.get(key, [])
        if not immune_ids:
            return await ctx.send("No configured immunities.")
        roles = [r for r in ctx.guild.roles if r.id in immune_ids]
        output = ", ".join([r.name for r in roles])
        return await ctx.send(output)
