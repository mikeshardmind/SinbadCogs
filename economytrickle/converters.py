import yaml
from redbot.core import commands


configable_guild_defaults = {
    "interval": 5,
    "level_xp_base": 100,
    "xp_lv_increase": 50,
    "maximum_level": None,
    "xp_per_interval": 10,
    "econ_per_interval": 20,
    "bonus_per_level": 5,
    "maximum_bonus": None,
    "extra_voice_xp": 0,
    "extra_message_xp": 0,
}


def settings_converter(user_input: str) -> dict:

    if user_input.startswith("```") and user_input.endswith("```"):
        user_input = "\n".join(user_input.split("\n")[1:-1])

    try:
        args = yaml.safe_load(user_input)
        assert all(k in configable_guild_defaults for k in args.keys())
    except (AssertionError, yaml.YAMLError):
        raise commands.BadArgument() from None

    if "interval" in args:
        try:
            assert args["interval"] == int(args["interval"])
            assert args["interval"] >= 5
        except AssertionError:
            raise commands.BadArgument(
                "Interval must be an integer value 5 or greater"
            ) from None

    for value in (
        "econ_per_interval",
        "bonus_per_level",
        "level_xp_base",
        "xp_lv_increase",
        "xp_per_interval",
        "extra_voice_xp",
        "extra_message_xp",
    ):
        if value in args:
            try:
                assert args[value] == int(args[value]) and args[value] >= 0
            except AssertionError:
                raise commands.BadArgument(
                    f"{value} must be a non-negative integer value"
                )

    for value in ("maximum_level", "maximum_bonus"):
        if value in args:
            try:
                assert args[value] is None or (
                    args[value] == int(args[value]) and args[value] >= 0
                )
            except AssertionError:
                raise commands.BadArgument(
                    f"{value} must be a non-negative integer value or `null`"
                )

    return args
