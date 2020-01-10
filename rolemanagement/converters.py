from __future__ import annotations

import argparse
import shlex
from abc import ABC
from dataclasses import dataclass, field
from typing import List, Optional, Set

import discord
from redbot.core.commands import RoleConverter, Context, BadArgument

RoleList = List[discord.Role]

_role_converter_instance = RoleConverter()


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class Filterable(ABC):
    hasany: RoleList
    hasall: RoleList
    none: RoleList
    noroles: bool
    hasperm: List[str]
    anyperm: List[str]
    notperm: List[str]
    add: RoleList
    remove: RoleList
    gt: Optional[int]
    lt: Optional[int]
    quantity: Optional[int]
    above: Optional[discord.Role]
    below: Optional[discord.Role]
    humans: bool
    bots: bool
    everyone: bool
    ctx: Context
    any_set: Set[discord.Member]
    all_set: Set[discord.Member]
    none_set: Set[discord.Member]
    minperms: discord.Permissions

    def _member_type_check(self, m: discord.Member) -> bool:
        return bool((self.bots and m.bot) or (self.humans and not m.bot))

    def _perms_check(self, m: discord.Member) -> bool:
        """ Returns True if a user passes the permission conditions """
        if self.notperm and any(
            bool(value and perm in self.notperm)
            for perm, value in iter(m.guild_permissions)
        ):
            return False

        if self.hasperm and not m.guild_permissions.is_superset(self.minperms):
            return False

        if self.anyperm and not any(
            bool(value and perm in self.anyperm)
            for perm, value in iter(m.guild_permissions)
        ):
            return False

        return True

    def _position_check(self, m: discord.Member) -> bool:
        return (
            False
            if (
                (self.above and m.top_role <= self.above)
                or (self.below and m.top_role >= self.below)
            )
            else True
        )

    def _quantity_check(self, m: discord.Member) -> bool:
        # 0 is a valid option for these, everyone role not counted
        role_count = len(m.roles) - 1

        return not any(
            (
                (self.noroles and role_count),
                (self.quantity is not None and role_count != self.quantity),
                (self.lt is not None and role_count >= self.lt),
                (self.gt is not None and role_count <= self.gt),
            )
        )

    def _membership_check(self, m: discord.Member) -> bool:
        return not bool(
            (self.hasany and m not in self.any_set)
            or (self.hasall and m not in self.all_set)
            or (self.none and m in self.none_set)
        )

    def get_members(self) -> Set[discord.Member]:
        if self.everyone:
            return set(self.ctx.guild.members)

        members = {
            m
            for m in self.ctx.guild.members
            if self._member_type_check(m)
            and self._membership_check(m)
            and self._position_check(m)
            and self._quantity_check(m)
            and self._perms_check(m)
        }
        return members


@dataclass()
class RoleSyntaxConverter:

    add: RoleList
    remove: RoleList

    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        parser = NoExitParser(
            description="Role management syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])
        try:
            vals = vars(parser.parse_args(shlex.split(argument)))
        except Exception:
            raise BadArgument()

        if not vals["add"] and not vals["remove"]:
            raise BadArgument("Must provide at least one action")

        for attr in ("add", "remove"):
            vals[attr] = [
                await _role_converter_instance.convert(ctx, r) for r in vals[attr]
            ]

        return cls(**vals)


@dataclass()
class ComplexActionConverter(Filterable):
    """
    --has-all roles
    --has-none roles
    --has-any roles
    --has-no-roles
    --has-exactly-nroles
    --has-more-than-nroles
    --has-less-than-nroles
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --above role
    --below role
    --add roles
    --remove roles
    --humans
    --bots
    --everyone
    """

    hasany: RoleList
    hasall: RoleList
    none: RoleList
    noroles: bool
    hasperm: List[str]
    anyperm: List[str]
    notperm: List[str]
    add: RoleList
    remove: RoleList
    gt: Optional[int]
    lt: Optional[int]
    quantity: Optional[int]
    above: Optional[discord.Role]
    below: Optional[discord.Role]
    humans: bool
    bots: bool
    everyone: bool
    ctx: Context
    all_set: Set[discord.Member] = field(init=False, default_factory=set)
    any_set: Set[discord.Member] = field(init=False, default_factory=set)
    none_set: Set[discord.Member] = field(init=False, default_factory=set)
    minperms: discord.Permissions = field(
        init=False, default_factory=discord.Permissions
    )

    def __post_init__(self):
        for role in self.hasall:
            self.all_set &= set(role.members)
        for role in self.hasany:
            self.any_set.update(role.members)
        for role in self.none:
            self.none_set.update(role.members)
        if self.hasperm:
            self.minperms.update(**{x: True for x in self.hasperm})

    @classmethod
    async def convert(cls, ctx: Context, argument: str):

        parser = NoExitParser(description="Role management syntax help", add_help=False)
        parser.add_argument("--has-any", nargs="*", dest="hasany", default=[])
        parser.add_argument("--has-all", nargs="*", dest="hasall", default=[])
        parser.add_argument("--has-none", nargs="*", dest="none", default=[])
        parser.add_argument(
            "--has-no-roles", action="store_true", default=False, dest="noroles"
        )
        parser.add_argument("--has-perms", nargs="*", dest="hasperm", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="anyperm", default=[])
        parser.add_argument("--not-perm", nargs="*", dest="notperm", default=[])
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])
        parser.add_argument(
            "--has-exactly-nroles", dest="quantity", type=int, default=None
        )
        parser.add_argument("--has-more-than-nroles", dest="gt", type=int, default=None)
        parser.add_argument("--has-less-than-nroles", dest="lt", type=int, default=None)
        parser.add_argument("--above", dest="above", type=str, default=None)
        parser.add_argument("--below", dest="below", type=str, default=None)
        hum_or_bot = parser.add_mutually_exclusive_group()
        hum_or_bot.add_argument(
            "--humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--bots", action="store_true", default=False, dest="bots"
        )
        hum_or_bot.add_argument(
            "--everyone", action="store_true", default=False, dest="everyone"
        )

        try:
            vals = vars(parser.parse_args(shlex.split(argument)))
        except Exception:
            raise BadArgument()

        if not vals["add"] and not vals["remove"]:
            raise BadArgument("Must provide at least one action")

        if not any(
            (
                vals["humans"],
                vals["everyone"],
                vals["bots"],
                vals["hasany"],
                vals["hasall"],
                vals["none"],
                vals["hasperm"],
                vals["notperm"],
                vals["anyperm"],
                vals["noroles"],
                bool(vals["quantity"] is not None),
                bool(vals["gt"] is not None),
                bool(vals["lt"] is not None),
                vals["above"],
                vals["below"],
            )
        ):
            raise BadArgument("You need to provide at least 1 search criterion")

        for attr in ("hasany", "hasall", "none", "add", "remove"):
            vals[attr] = [
                await _role_converter_instance.convert(ctx, r) for r in vals[attr]
            ]

        for attr in ("below", "above"):
            if vals[attr] is None:
                continue
            vals[attr] = await _role_converter_instance.convert(ctx, vals[attr])

        for attr in ("hasperm", "anyperm", "notperm"):

            vals[attr] = [
                i.replace("_", " ").lower().replace(" ", "_").replace("server", "guild")
                for i in vals[attr]
            ]
            if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                raise BadArgument("You gave an invalid permission")

        return cls(ctx=ctx, **vals)


@dataclass()
class ComplexSearchConverter(Filterable):
    """
    --has-all roles
    --has-none roles
    --has-any roles
    --has-no-roles
    --has-exactly-nroles
    --has-more-than-nroles
    --has-less-than-nroles
    --humans
    --bots
    --above role
    --below role
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --everyone
    --csv
    """

    hasany: RoleList
    hasall: RoleList
    none: RoleList
    csv: bool
    noroles: bool
    hasperm: List[str]
    anyperm: List[str]
    notperm: List[str]
    gt: Optional[int]
    lt: Optional[int]
    quantity: Optional[int]
    above: Optional[discord.Role]
    below: Optional[discord.Role]
    humans: bool
    bots: bool
    everyone: bool
    ctx: Context
    all_set: Set[discord.Member] = field(init=False, default_factory=set)
    any_set: Set[discord.Member] = field(init=False, default_factory=set)
    none_set: Set[discord.Member] = field(init=False, default_factory=set)
    minperms: discord.Permissions = field(
        init=False, default_factory=discord.Permissions
    )

    def __post_init__(self):
        for role in self.hasall:
            self.all_set &= set(role.members)
        for role in self.hasany:
            self.any_set.update(role.members)
        for role in self.none:
            self.none_set.update(role.members)
        if self.hasperm:
            self.minperms.update(**{x: True for x in self.hasperm})

    @classmethod
    async def convert(cls, ctx: Context, argument: str):
        parser = NoExitParser(description="Role management syntax help", add_help=False)
        parser.add_argument("--has-any", nargs="*", dest="hasany", default=[])
        parser.add_argument("--has-all", nargs="*", dest="hasall", default=[])
        parser.add_argument("--has-none", nargs="*", dest="none", default=[])
        parser.add_argument(
            "--has-no-roles", action="store_true", default=False, dest="noroles"
        )
        parser.add_argument("--has-perms", nargs="*", dest="hasperm", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="anyperm", default=[])
        parser.add_argument("--not-perm", nargs="*", dest="notperm", default=[])
        parser.add_argument("--csv", action="store_true", default=False)
        parser.add_argument(
            "--has-exactly-nroles", dest="quantity", type=int, default=None
        )
        parser.add_argument("--has-more-than-nroles", dest="gt", type=int, default=None)
        parser.add_argument("--has-less-than-nroles", dest="lt", type=int, default=None)
        parser.add_argument("--above", dest="above", type=str, default=None)
        parser.add_argument("--below", dest="below", type=str, default=None)
        hum_or_bot = parser.add_mutually_exclusive_group()
        hum_or_bot.add_argument(
            "--humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--bots", action="store_true", default=False, dest="bots"
        )
        hum_or_bot.add_argument(
            "--everyone", action="store_true", default=False, dest="everyone"
        )
        try:
            vals = vars(parser.parse_args(shlex.split(argument)))
        except Exception:
            raise BadArgument()

        if not any(
            (
                vals["humans"],
                vals["everyone"],
                vals["bots"],
                vals["hasany"],
                vals["hasall"],
                vals["none"],
                vals["hasperm"],
                vals["notperm"],
                vals["anyperm"],
                vals["noroles"],
                bool(vals["quantity"] is not None),
                bool(vals["gt"] is not None),
                bool(vals["lt"] is not None),
                vals["above"],
                vals["below"],
            )
        ):
            raise BadArgument("You need to provide at least 1 search criterion")

        for attr in ("hasany", "hasall", "none"):
            vals[attr] = [
                await _role_converter_instance.convert(ctx, r) for r in vals[attr]
            ]

        for attr in ("below", "above"):
            if vals[attr] is None:
                continue
            vals[attr] = await _role_converter_instance.convert(ctx, vals[attr])

        for attr in ("hasperm", "anyperm", "notperm"):

            vals[attr] = [
                i.replace("_", " ").lower().replace(" ", "_").replace("server", "guild")
                for i in vals[attr]
            ]
            if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                raise BadArgument("You gave an invalid permission")

        return cls(ctx=ctx, **vals)
