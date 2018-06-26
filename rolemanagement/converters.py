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
