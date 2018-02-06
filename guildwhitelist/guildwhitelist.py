import asyncio
from typing import List, Union
import logging

import discord
from discord.ext import commands

from redbot.core.i18n import CogI18n
from redbot.core import Config
from redbot.core.utils.chat_formatting import box, pagify
from .dataconverter import DataConverter

_ = CogI18n("GuildWhitelist", __file__)

log = logging.getLogger('red.guildwhitelist')


class GuildWhitelist:

    default_globals = {
        'whitelist': []
    }

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_global(**self.default_globals)

    async def on_guild_join(self, guild: discord.Guild):
        async with self.config.whitelist() as whitelist:
            if not any(
                x in whitelist
                for x in (guild.id, guild.owner.id)
            ) and not (await self.bot.is_owner(guild.owner)):
                log.info('leaving {0.id} {0.name}'.format(guild))
                await guild.leave()
