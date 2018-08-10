import argparse
import shlex
from redbot.core.commands import RoleConverter, Context, BadArgument
import discord


class DynoSyntaxConverter(RoleConverter):

    async def convert(self, ctx: Context, argument: str):
        args = [c.strip() for c in argument.split(",")]
        ret: dict = {"+": [], "-": []}

        for arg in args:
            ret[arg[0]].append(
                await super(DynoSyntaxConverter, self).convert(ctx, arg[1:])
            )

        if not (ret["+"] or ret["-"]):
            raise BadArgument("This requires at least one role operation.")

        if not set(ret["+"]).isdisjoint(ret["-"]):
            raise BadArgument("That's not a valid search.")
        return ret


class RoleSyntaxConverter(RoleConverter):

    async def convert(self, ctx: Context, argument: str):
        parser = argparse.ArgumentParser(
            description="Role management syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])

        vals = vars(parser.parse_args(shlex.split(argument)))

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
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --add roles
    --remove roles
    --only-humans
    --only-bots
    --everyone
    """

    async def convert(self, ctx: Context, argument: str) -> dict:

        parser = argparse.ArgumentParser(
            description="Role management syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--has-any", nargs="*", dest="any", default=[])
        parser.add_argument("--has-all", nargs="*", dest="all", default=[])
        parser.add_argument("--has-none", nargs="*", dest="none", default=[])
        parser.add_argument("--has-perms", nargs="*", dest="hasperm", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="anyperm", default=[])
        parser.add_argument("--not-perm", nargs="*", dest="notperm", default=[])
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])
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

        vals = vars(parser.parse_args(shlex.split(argument)))

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
            )
        ):
            raise BadArgument("You need to provide at least 1 search criterion")

        for attr in ("any", "all", "none", "add", "remove"):
            vals[attr] = [
                await super(ComplexActionConverter, self).convert(ctx, r)
                for r in vals[attr]
            ]

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
    --only-humans
    --only-bots
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --everyone
    --csv
    """

    async def convert(self, ctx: Context, argument: str) -> dict:
        parser = argparse.ArgumentParser(
            description="Role management syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--has-any", nargs="*", dest="any", default=[])
        parser.add_argument("--has-all", nargs="*", dest="all", default=[])
        parser.add_argument("--has-none", nargs="*", dest="none", default=[])
        parser.add_argument("--has-perms", nargs="*", dest="hasperm", default=[])
        parser.add_argument("--any-perm", nargs="*", dest="anyperm", default=[])
        parser.add_argument("--not-perm", nargs="*", dest="notperm", default=[])
        parser.add_argument("--csv", action="store_true", default=False)
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

        vals = vars(parser.parse_args(shlex.split(argument)))

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
            )
        ):
            raise BadArgument("You need to provide at least 1 search criterion")

        for attr in ("any", "all", "none"):
            vals[attr] = [
                await super(ComplexSearchConverter, self).convert(ctx, r)
                for r in vals[attr]
            ]

        for attr in ("hasperm", "anyperm", "notperm"):

            vals[attr] = [
                i.replace("_", " ").lower().replace(" ", "_").replace("server", "guild")
                for i in vals[attr]
            ]
            if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                raise BadArgument("You gave an invalid permission")

        return vals
