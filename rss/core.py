import asyncio
import string
from typing import Optional, List
from datetime import datetime

import aiohttp
import feedparser
import discord

from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n

from .cleanup import html_to_text


T_ = Translator("RSS", __file__)

_ = lambda s: s
# Strings in here are guarded

#
_ = T_

USABLE_FIELDS = [
    "author",
    "author_detail",
    "comments",
    "content",
    "contributors",
    "created",
    "link",
    "name",
    "publisher",
    "publisher_detail",
    "source",
    "summary", 
    "summary_detail",
    "tags",
    "title",
    "title_detail",
]

@cog_i18n(_)
class RSS(commands.Cog):
    """
    An RSS cog. See `[p]help RSS` for detailed usage.
    
    Sponsored by aikaterna, the most helpful of cats.
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "0.0.0"
    __flavor_text__ = "Still unfinished, UX needed to be rewritten...."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(feeds={})
        self.session = aiohttp.ClientSession()
        self.bg_loop_task = self.bot.create_task(self.bg_loop())

    def __unload(self):
        self.bg_loop_task.cancel()
        self.bot.schedule_task(self.session.close())

    __del__ = (
        __unload
    )  # This really shouldn't be neccessary, but I'll verify this later.

    async def should_embed(self, guild: discord.Guild) -> bool:
        guild_setting = await self.bot.db.guild(guild).embeds()
        if guild_setting is not None:
            return guild_setting
        return await self.bot.db.embeds()

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        timeout = aiohttp.client.ClientTimeout(total=5)
        try:
            async with self.session.get(url, timeout=timeout) as response:
                data = await response.read()
        except aiohttp.ClientError:
            return None

        ret = feedparser.parse(data)
        if ret.bozo:
            return None
        return ret

    async def format_and_send(
        self,
        *,
        destination: discord.abc.Messageable,
        response: feedparser.FeedParserDict,
        feed_settings: dict,
        embed_default: bool,
        force: bool = False,
    ) -> Optional[List[int]]:
        """
        Formats and sends, 
        returns the integer timestamp of latest entry in the feed which was sent
        """

        use_embed = feed_settings.get("embed_override", None)
        if use_embed is None:
            use_embed = embed_default

        if force:
            try:
                to_send = [response.entries[0]]
            except IndexError:
                return None
        else:
            last = tuple(feed_settings.get("last", (0,)))
            to_send = sorted(
                [e for e in response.entries if tuple(e.published_parsed) > last],
                key=lambda e: tuple(e.published_parsed),
            )

        last_sent = None
        for entry in to_send:
            color = destination.guild.me.color
            kwargs = self.format_post(
                entry, use_embed, color, feed_settings.get("template", None)
            )
            try:
                await self.bot.send_filtered(destination, **kwargs)
            except discord.HTTPException:
                continue
            last_sent = list(entry.published_parsed)

        return last_sent

    @staticmethod
    def format_post(entry, embed: bool, color, template=None) -> dict:

        if template is None:
            if embed:
                _template = "[$title]($link)"
            else:
                _template = "$title: <$link>"

        template = string.Template(_template)

        escaped_usable_fields = {
            k: (v if not isinstance(v, str) else html_to_text(v))
            for k, v in entry if k in USABLE_FIELDS and v
        } 

        content = template.safe_substitute(**escaped_usable_fields)

        if embed:
            timestamp = datetime(*entry.published_parsed[:6])
            embed_data = discord.Embed(
                description=content, color=color, timestamp=timestamp
            )
            embed_data.set_footer(text=_("Published "))
            return {"content": None, "embed": embed_data}
        else:
            return {"content": content, "embed": None}

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while self.bot.get_cog("RSS") == self:
            await asyncio.sleep(600)  # TODO: configureable
            feeds_fetched = {}
            default_embed_settings = {}

            channel_data = await self.config.all_channels()
            to_update = channel_data.copy()
            for channel_id, data in channel_data.items():

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    continue
                if channel.guild not in default_embed_settings:
                    should_embed = await self.should_embed(channel.guild)
                    default_embed_settings[channel.guild] = should_embed
                else:
                    should_embed = default_embed_settings[channel.guild]

                for feed_name, feed in data["feeds"].items():
                    url = feed["url"]
                    if url in feeds_fetched:
                        response = feeds_fetched[url]
                    else:
                        response = await self.fetch_feed(url)
                        feeds_fetched[url] = response

                    if response:
                        try:
                            last = await self.format_and_send(
                                destination=channel,
                                response=response,
                                feed_settings=feed,
                                embed_default=should_embed,
                            )
                        except Exception:
                            pass
                        else:
                            await self.config.channel(channel).set_raw(
                                feed_name, "last", value=last
                            )
