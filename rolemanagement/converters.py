import argparse
import shlex
from redbot.core import commands


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


class ComplexRoleSyntaxConverter(RoleSyntaxConverter):
    def __init__(self):
        super(ComplexRoleSyntaxConverter, self).__init__()

    async def convert(self, ctx: commands.Context, argument: str):
        args = [c.strip() for c in argument.split(";")]
        if len(args) != 2:
            raise commands.BadArgument("Requires both a search and operation")

        ret = [
            (await super(ComplexRoleSyntaxConverter, self).convert(ctx, arg))
            for arg in args
        ]
        return ret


class ComplexActionConverter(commands.RoleConverter):
    """
    --has-all roles
    --has-none roles
    --has-any roles
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
        parser.add_argument("--has-any", nargs="*", dest="any")
        parser.add_argument("--has-all", nargs="*", dest="all")
        parser.add_argument("--has-none", nargs="*", dest="none")
        parser.add_argument("--add", nargs="*", dest="add")
        parser.add_argument("--remove", nargs="*", dest="remove")
        hum_or_bot = parser.add_mutually_exclusive_group()
        hum_or_bot.add_argument(
            "--only-humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--only-bots", action="store_true", default=False, dest="bots"
        )
        hum_or_bot.add_argument("--everyone", action="store_true", default=False)

        vals = vars(parser.parse_args(shlex.split(arg))

        if not (vals['add'] or vals['remove']):
            raise commands.BadArgument("Must provide at least one action")
        if not any(
            (vals['humans'], vals['everyone'], vals['bots'], vals['any'], vals['all'], vals['none'])
        ):
            raise commands.BadArgument(
                "You need to provide at least 1 search criterion"
            )

        for attr in ("any", "all", "none", "add", "remove"):
            vals[attr] = [await super().convert(r) for r in vals[attr]]
        return vals


class ComplexSearchConverter(commands.RoleConverter):
    """
    --has-all roles
    --has-none roles
    --has-any roles
    --only-humans
    --only-bots
    --csv
    --embed
    """

    def __init__(self):
        super(ComplexActionConverter, self).__init__()

    async def convert(self, ctx: commands.Context, arg: str) -> dict:

        parser = argparse.ArgumentParser(
            description="Role management syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--has-any", nargs="*", dest="any")
        parser.add_argument("--has-all", nargs="*", dest="all")
        parser.add_argument("--has-none", nargs="*", dest="none")
        output = parser.add_mutually_exclusive_group()
        output.add_argument("--csv", action="store_true", default=False)
        output.add_argument("--embed", action="store_true", default=False)
        hum_or_bot = parser.add_mutually_exclusive_group()
        hum_or_bot.add_argument(
            "--only-humans", action="store_true", default=False, dest="humans"
        )
        hum_or_bot.add_argument(
            "--only-bots", action="store_true", default=False, dest="bots"
        )
        hum_or_bot.add_argument("--everyone", action="store_true", default=False)

        vals = parser.parse_args(shlex.split(arg))

        if not any(
            (vals.humans, vals.everyone, vals.bots, vals.any, vals.all, vals.none)
        ):
            raise commands.BadArgument(
                "You need to provide at least 1 search criterion"
            )

        ret = vars(vals)
        for attr in ("any", "all", "none", "add", "remove"):
            ret[attr] = [await super().convert(r) for r in ret[attr]]
        return ret
