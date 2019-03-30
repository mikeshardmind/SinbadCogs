import argparse
import shlex
from redbot.core.commands import RoleConverter, Context, BadArgument
import discord
from typing import Dict


class RoleEmojiMap(RoleConverter):
    def __init__(self):
        super().__init__()

    async def convert(self, ctx: Context, argument: str) -> Dict[discord.Role, emoji]:

        arg_list = shlex.split(argument)
        mapping = {}

        if len(arg_list) % 2:
            raise BadArgument()

        iterator = iter(arg_list)

        for role_string in iterator:
            emoji_string = next(iterator)  # I'm being lazy af.
            role = await super().convert(ctx, role_string)
            # can't validate emoji here without a twemoji dependency
            # and excluding some edge cases.
            mapping[role] = emoji_string

        return mapping


class NoExitParser(argparse.ArgumentParser):
    def error(self, message):
        raise BadArgument()


class RoleSyntaxConverter(RoleConverter):
    def __init__(self):
        super().__init__()

    async def convert(self, ctx: Context, argument: str):
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
                await super(RoleSyntaxConverter, self).convert(ctx, r)
                for r in vals[attr]
            ]

        return vals


class ComplexActionConverter(RoleConverter):
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
    --only-humans
    --only-bots
    --everyone
    """

    def __init__(self):
        super().__init__()

    async def convert(self, ctx: Context, argument: str) -> dict:

        parser = NoExitParser(description="Role management syntax help", add_help=False)
        parser.add_argument("--has-any", nargs="*", dest="any", default=[])
        parser.add_argument("--has-all", nargs="*", dest="all", default=[])
        parser.add_argument("--has-none", nargs="*", dest="none", default=[])
        parser.add_argument(
            "--has-no-roles", action="store_true", default=False, dest="noroles"
        )
        parser.add_argument("--has-perms", nargs="*", dest="hasperm", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="anyperm", default=[])
        parser.add_argument("--not-perm", nargs="*", dest="notperm", default=[])
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])
        parser.add_argument("--has-exactly-nroles", dest="quantity", type=int)
        parser.add_argument("--has-more-than-nroles", dest="gt", type=int, default=None)
        parser.add_argument("--has-less-than-nroles", dest="lt", type=int, default=None)
        parser.add_argument("--above", dest="above", type=str, default=None)
        parser.add_argument("--below", dest="below", type=str, default=None)
        hum_or_bot = parser.add_mutually_exclusive_group()
        hum_or_bot.add_argument(
            "--only-humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--only-bots", action="store_true", default=False, dest="bots"
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
                vals["any"],
                vals["all"],
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

        for attr in ("any", "all", "none", "add", "remove"):
            vals[attr] = [
                await super(ComplexActionConverter, self).convert(ctx, r)
                for r in vals[attr]
            ]

        for attr in ("below", "above"):
            if vals[attr] is None:
                continue
            vals[attr] = await super(ComplexActionConverter, self).convert(
                ctx, vals[attr]
            )

        for attr in ("hasperm", "anyperm", "notperm"):

            vals[attr] = [
                i.replace("_", " ").lower().replace(" ", "_").replace("server", "guild")
                for i in vals[attr]
            ]
            if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                raise BadArgument("You gave an invalid permission")

        return vals


class ComplexSearchConverter(RoleConverter):
    """
    --has-all roles
    --has-none roles
    --has-any roles
    --has-no-roles
    --has-exactly-nroles
    --has-more-than-nroles
    --has-less-than-nroles
    --only-humans
    --only-bots
    --above role
    --below role
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --everyone
    --csv
    """

    def __init__(self):
        super().__init__()

    async def convert(self, ctx: Context, argument: str) -> dict:
        parser = NoExitParser(description="Role management syntax help", add_help=False)
        parser.add_argument("--has-any", nargs="*", dest="any", default=[])
        parser.add_argument("--has-all", nargs="*", dest="all", default=[])
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
            "--only-humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--only-bots", action="store_true", default=False, dest="bots"
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
                vals["any"],
                vals["all"],
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

        for attr in ("any", "all", "none"):
            vals[attr] = [
                await super(ComplexSearchConverter, self).convert(ctx, r)
                for r in vals[attr]
            ]

        for attr in ("below", "above"):
            if vals[attr] is None:
                continue
            vals[attr] = await super(ComplexSearchConverter, self).convert(
                ctx, vals[attr]
            )

        for attr in ("hasperm", "anyperm", "notperm"):

            vals[attr] = [
                i.replace("_", " ").lower().replace(" ", "_").replace("server", "guild")
                for i in vals[attr]
            ]
            if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                raise BadArgument("You gave an invalid permission")

        return vals
