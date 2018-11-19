import asyncio
import string
from typing import Optional, List, cast, no_type_check
from datetime import datetime

import aiohttp
import feedparser
import discord

from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify

from .cleanup import html_to_text
from .converters import tristate  # typing: ignore


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
    An RSS cog.
    
    Sponsored by aikaterna, the most helpful of cats.
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "1.0.0a"
    __flavor_text__ = "Needs some testing to be sure..."

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(feeds={})
        self.session = aiohttp.ClientSession()
        self.bg_loop_task = self.bot.loop.create_task(self.bg_loop())

    def __unload(self):
        self.bg_loop_task.cancel()
        self.bot.schedule_task(self.session.close())

    __del__ = __unload  
    # This really shouldn't be neccessary, but I'll verify this later.

    def clear_feed(self, channel, feedname):
        """
        This is abuse.
        """
        return self.config.channel(channel).clear_raw("feeds", feedname)

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
            for k, v in entry
            if k in USABLE_FIELDS and v
        }

        content = template.safe_substitute(**escaped_usable_fields)

        if embed:
            if len(content) > 5800:
                content = content[:5800] + _("... (Feed data too long)")
            timestamp = datetime(*entry.published_parsed[:6])
            embed_data = discord.Embed(
                description=content, color=color, timestamp=timestamp
            )
            embed_data.set_footer(text=_("Published "))
            return {"content": None, "embed": embed_data}
        else:
            if len(content) > 1950:
                content = content[:1950] + _("... (Feed data too long)")
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

    # commands go here

    @commands.group()
    async def rss(self, ctx: commands.Context):
        """
        Configuration for rss
        """
        pass

    @commands.cooldown(3, 60, type=commands.BucketType.user)
    @rss.command()
    async def addfeed(
        self,
        ctx: commands.Context,
        name: str, 
        url: str,
        channel: Optional[discord.TextChannel],
    ):
        """
        Adds a feed to the current, or a provided channel
        """

        channel = channel or ctx.channel

        async with self.config.channel(channel).feeds() as feeds:
            if name in feeds:
                return await ctx.send(_("That name is already in use."))

            response = await self.fetch_feed(url)

            if response is None:
                return await ctx.send(_("That didn't seem to be a valid rss feed."))
        
            else:
                feeds.update(
                    {
                        name: {
                            'url': url,
                            "template": None,
                            "embed_override": None,
                            "last": list(ctx.message.created_at.timetuple()[:6]),
                        }
                    }
                )

        await ctx.tick()

    @rss.command(name="list")
    async def list_feeds(self, ctx: commands.Context, channel: Optional[discord.TextChannel]):
        """
        Lists the current feeds (and their locations) 
        for the current channel, or a provided one.
        """

        channel = channel or ctx.channel

        data = await self.config.channel(channel).feeds()

        if await ctx.embed_requested():
            output = "\n".join(
                ["{name}: {url}".format(name=k, url=v['url']) for k, v in data.items()]
            )
            for page in pagify(output, page_length=6000):
                await ctx.send(
                    discord.Embed(description=page, color=(await ctx.embed_color()))
                )
        else:
            output = "\n".join(
                ["{name}: <{url}>".format(name=k, url=v['url']) for k, v in data.items()]
            )
            for page in pagify(output):
                await ctx.send(page)

    @rss.command(name="remove")
    async def remove_feed(self, ctx, name: str, channel: Optional[discord.TextChannel]):
        """
        removes a feed from the current channel, or from a provided channel

        If the feed is currently being fetched, there may still be a final update
        after this.
        """
        channel = channel or ctx.channel
        await self.clear_feed(channel, name)
        await ctx.tick()

    
    @rss.command(name="embed")
    @no_type_check
    async def set_embed(
        self, ctx, feed: str, setting: tristate, channel: Optional[discord.TextChannel]
    ):
        """
        Sets if a specific feed should 
            use an embed, 
            not use an embed, 
            or (default) use the bot setting to determine embed usage.

        Valid Settings for this are:
            True
            False
            Default
        """

        channel = channel or ctx.channel
        await self.config.channel(channel).set_raw("feeds", feed, "embed_override", value=setting)
        await ctx.tick()

    @rss.command(name="template")
    async def set_template(self, ctx, feed, template, channel: Optional[discord.TextChannel]):
        """
        Sets formatting for the specified feed in this, or a provided channel

        The following have special meaning based on their content in the RSS feed data:

        $author
        $author_detail
        $comments
        $content
        $contributors
        $created
        $link
        $name
        $publisher
        $publisher_detail
        $source
        $summary
        $summary_detail
        $tags
        $title
        $title_detail

        """

        channel = channel or ctx.channel

        await self.config.channel(channel).set_raw("feeds", feed, "template", value=template)
        await ctx.tick()

    @rss.command(name="resettemplate")
    async def reset_template(self, ctx, feed, channel: Optional[discord.TextChannel]):
        """
        Resets the template in use for a specific feed in this, or a provided channel
        """
        channel = channel or ctx.channel
        await self.config.channel(channel).clear_raw("feeds", feed, "template")
        await ctx.tick()