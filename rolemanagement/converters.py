import argparse
import shlex
from redbot.core import commands
import discord


class RoleSyntaxConverter(commands.RoleConverter):
    def __init__(self):
        super(RoleSyntaxConverter, self).__init__()

    async def convert(self, ctx: commands.Context, argument: str):
        args = [c.strip() for c in argument.split(",")]
        ret = {"+": [], "-": []}

        for arg in args:
            ret[arg[0]].append(
                await super(RoleSyntaxConverter, self).convert(ctx, arg[1:])
            )

        if not (ret["+"] or ret["-"]):
            raise commands.BadArgument("This requires at least one role operation.")

        if not set(ret["+"]).isdisjoint(ret["-"]):
            raise commands.BadArgument("That's not a valid search.")
        return ret


class ComplexActionConverter(commands.RoleConverter):
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

    def __init__(self):
        super(ComplexActionConverter, self).__init__()

    async def convert(self, ctx: commands.Context, arg: str) -> dict:

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
        hum_or_bot.add_argument("--everyone", action="store_true", default=False)

        vals = vars(parser.parse_args(shlex.split(arg)))

        if not vals["add"] and not vals["remove"]:
            raise commands.BadArgument("Must provide at least one action")

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
            raise commands.BadArgument(
                "You need to provide at least 1 search criterion"
            )

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
                raise commands.BadArgument("You gave an invalid permission")

        return vals


class ComplexSearchConverter(commands.RoleConverter):
    """
    --has-all roles
    --has-none roles
    --has-any roles
    --only-humans
    --only-bots
    --has-perm permissions
    --any-perm permissions
    --not-perm permissions
    --csv
    """

    def __init__(self):
        super(ComplexSearchConverter, self).__init__()

    async def convert(self, ctx: commands.Context, arg: str) -> dict:
        try:
            parser = argparse.ArgumentParser(
                description="Role management syntax help",
                add_help=False,
                allow_abbrev=True,
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
            hum_or_bot.add_argument("--everyone", action="store_true", default=False)

            vals = vars(parser.parse_args(shlex.split(arg)))

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
                raise commands.BadArgument(
                    "You need to provide at least 1 search criterion"
                )

            for attr in ("any", "all", "none"):
                vals[attr] = [
                    await super(ComplexSearchConverter, self).convert(ctx, r)
                    for r in vals[attr]
                ]

            for attr in ("hasperm", "anyperm", "notperm"):

                vals[attr] = [
                    i.replace("_", " ")
                    .lower()
                    .replace(" ", "_")
                    .replace("server", "guild")
                    for i in vals[attr]
                ]
                if any(perm not in dir(discord.Permissions) for perm in vals[attr]):
                    raise commands.BadArgument("You gave an invalid permission")

            return vals
        except Exception as e:
            print(e)
