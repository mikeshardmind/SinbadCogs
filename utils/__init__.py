import random

import discord


def random_hue_half_saturate() -> discord.Color:
    return discord.Color.from_hsv(random.random(), 0.5, 1)
