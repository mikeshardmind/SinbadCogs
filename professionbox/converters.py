from redbot.core import commands
import contextlib
import yaml


valid_profs = [
    "Alchemist",
    "Farmer",
    "Fisherman",
    "Hunter",
    "Lumberjack",
    "Miner",
    "Artificer",
    "Carver",
    "Handyman",
    "Jeweller",
    "Shoemaker",
    "Smith",
    "Tailor",
    "Carvmagus",
    "Costumagus",
    "Jewelmagus",
    "Shoemagus",
    "Smithmagus",
]


class ProfessionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if arg.strip().title() in valid_profs:
            return arg.strip().title()
        raise commands.BadArgument("That isn't a valid profession.")


class ProfessionLevelConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> int:
        with contextlib.suppress(Exception):
            ret = int(arg)
            if 0 < ret <= 200:
                return ret

        raise commands.BadArgument("Expected a profession level between 1 and 200")


class MultiProfConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, arg: str) -> dict:
        try:
            if arg.startswith("```") and arg.endswith("```"):
                arg = "\n".join(arg.split("\n")[1:-1])
            parsed = yaml.safe_load(arg)
            parsed = {k.strip().title(): int(v) for k, v in parsed.items()}
        except Exception:
            raise commands.BadArgument(
                "Expected format of \n```yaml\nProfession name: level\n```"
            )
        for prof, level in parsed.items():
            if not (prof in valid_profs and (0 < level <= 200)):
                raise commands.BadArgument(
                    "Expected format of \n```yaml\nProfession name: level\n```"
                )
        else:
            return parsed
