from __future__ import annotations

import asyncio
import logging
import string
import urllib.parse
from datetime import datetime
from functools import partial
from types import MappingProxyType
from typing import Any, Dict, Generator, List, Optional, cast

import aiohttp
import discord
import feedparser
from bs4 import BeautifulSoup as bs4
from redbot.core import checks, commands
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, pagify

from .cleanup import html_to_text
from .converters import FieldAndTerm, NonEveryoneRole, TriState

log = logging.getLogger("red.sinbadcogs.rss")

DONT_HTML_SCRUB = ["link", "source", "updated", "updated_parsed"]

USABLE_FIELDS = [
    "author",
    "author_detail",
    "description",
    "comments",
    "content",
    "contributors",
    "created",
    "updated",
    "updated_parsed",
    "link",
    "name",
    "published",
    "published_parsed",
    "publisher",
    "publisher_detail",
    "source",
    "summary",
    "summary_detail",
    "tags",
    "title",
    "title_detail",
]

USABLE_TEXT_FIELDS = [
    f
    for f in USABLE_FIELDS
    if f
    not in ("published", "published_parsed", "updated", "updated_parsed", "created",)
]


def debug_exc_log(lg: logging.Logger, exc: Exception, msg: str = "Exception in RSS"):
    if lg.getEffectiveLevel() <= logging.DEBUG:
        lg.exception(msg, exc_info=exc)


class RSS(commands.Cog):
    """
    An RSS cog.
    """

    __author__ = "mikeshardmind(Sinbad)"
    __version__ = "340.0.3"

    async def red_delete_data_for_user(self, **kwargs):
        """ Nothing to delete """
        return

    def format_help_for_context(self, ctx):
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\nCog Version: {self.__version__}"

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_channel(feeds={})
        self.session = aiohttp.ClientSession()
        self.bg_loop_task: Optional[asyncio.Task] = None

    def init(self):
        self.bg_loop_task = asyncio.create_task(self.bg_loop())

        def done_callback(fut: asyncio.Future):

            try:
                fut.exception()
            except asyncio.CancelledError:
                pass
            except asyncio.InvalidStateError as exc:
                log.exception(
                    "We somehow have a done callback when not done?", exc_info=exc
                )
            except Exception as exc:
                log.exception("Unexpected exception in rss: ", exc_info=exc)

        self.bg_loop_task.add_done_callback(done_callback)

    def cog_unload(self):
        if self.bg_loop_task:
            self.bg_loop_task.cancel()
        asyncio.create_task(self.session.close())

    async def should_embed(self, channel: discord.TextChannel) -> bool:
        ret: bool = await self.bot.embed_requested(channel, channel.guild.me)
        return ret

    async def fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        timeout = aiohttp.client.ClientTimeout(total=15)
        try:
            async with self.session.get(url, timeout=timeout) as response:
                data = await response.read()
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return None
        except Exception as exc:
            debug_exc_log(
                log,
                exc,
                f"Unexpected exception type {type(exc)} encountered for feed url: {url}",
            )
            return None

        ret = feedparser.parse(data)
        self.bot.dispatch(
            # dispatch is versioned.
            # To remain compatible, accept kwargs and check version
            #
            # version: 1
            # response_regerator: Callable[[], feedparser.FeedParserDict]
            # bozo: Whether this was already a junk response.
            #
            # This may be dispatched any time a feed is fetched,
            # and if you use this, you should compare with prior info
            # The response regeneration exists to remove potential
            # of consumers accidentally breaking the cog by mutating
            # a response which has not been consumed by the cog yet.
            # re-parsing is faster than a deepcopy, and prevents needing it
            # should nothing be using the listener.
            "sinbadcogs_rss_fetch",
            listener_version=1,
            response_regenerator=partial(feedparser.parse, data),
            bozo=ret.bozo,
        )
        if ret.bozo:
            log.debug(f"Feed url: {url} is invalid.")
            return None
        return ret

    @staticmethod
    def process_entry_time(x):
        if "published_parsed" in x:
            return tuple(x.get("published_parsed"))[:5]
        if "updated_parsed" in x:
            return tuple(x.get("updated_parsed"))[:5]
        return (0,)

    async def find_feeds(self, site: str) -> List[str]:
        """
        Attempts to find feeds on a page
        """

        async with self.session.get(site) as response:
            data = await response.read()

        possible_feeds = set()
        html = bs4(data)
        feed_urls = html.findAll("link", rel="alternate")
        if len(feed_urls) > 1:
            for f in feed_urls:
                if t := f.get("type", None):
                    if "rss" in t or "xml" in t:
                        if href := f.get("href", None):
                            possible_feeds.add(href)

        parsed_url = urllib.parse.urlparse(site)
        scheme, hostname = parsed_url.scheme, parsed_url.hostname
        if scheme and hostname:
            base = "://".join((scheme, hostname))
            atags = html.findAll("a")

            for a in atags:
                if href := a.get("href", None):
                    if "xml" in href or "rss" in href or "feed" in href:
                        possible_feeds.add(base + href)

        return [site for site in possible_feeds if await self.fetch_feed(site)]

    async def format_and_send(
        self,
        *,
        destination: discord.TextChannel,
        response: feedparser.FeedParserDict,
        feed_name: str,
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

        assert isinstance(response.entries, list), "mypy"  # nosec

        match_rule = feed_settings.get("match_req", [])

        def meets_rule(entry):
            if not match_rule:
                return True

            field_name, term = match_rule

            d = getattr(entry, field_name, None)
            if not d:
                return False
            elif isinstance(d, list):
                for item in d:
                    if term in item:
                        return True
                return False
            elif isinstance(d, str):
                return term in d.casefold()

            return False

        if force:
            _to_send = next(filter(meets_rule, response.entries), None)
            if not _to_send:
                return None
            to_send = [_to_send]
        else:
            last = feed_settings.get("last", None)
            last = tuple((last or (0,))[:5])

            to_send = sorted(
                [
                    e
                    for e in response.entries
                    if self.process_entry_time(e) > last and meets_rule(e)
                ],
                key=self.process_entry_time,
            )

        last_sent = None
        roles = feed_settings.get("role_mentions", [])
        for entry in to_send:
            color = destination.guild.me.color

            kwargs = self.format_post(
                entry, use_embed, color, feed_settings.get("template", None), roles
            )
            try:
                r = discord.http.Route(
                    "POST", "/channels/{channel_id}/messages", channel_id=destination.id
                )
                if em := kwargs.pop("embed", None):
                    assert isinstance(em, discord.Embed), "mypy"  # nosec
                    kwargs["embed"] = em.to_dict()
                kwargs["allowed_mentions"] = {"parse": [], "roles": roles}

                await self.bot.http.request(r, json=kwargs)
            except discord.HTTPException as exc:
                debug_exc_log(log, exc, "Exception while sending feed.")
                self.bot.dispatch(
                    # If you want to use this, make your listener accept
                    # what you need from this + **kwargs to not break if I add more
                    # This listener is versioned.
                    # you should not mutate the feedparser classes.
                    #
                    # version: 1
                    # destination: discord.TextChannel
                    # feed_name: str
                    # feedparser_entry: feedparser.FeedParserDict
                    # feed_settings: MappingProxy
                    # forced_update: bool
                    "sinbadcogs_rss_send_fail",
                    listener_version=1,
                    destination=destination,
                    feed_name=feed_name,
                    feedparser_entry=entry,
                    feed_settings=MappingProxyType(feed_settings),
                    forced_update=force,
                )
            else:
                self.bot.dispatch(
                    # If you want to use this, make your listener accept
                    # what you need from this + **kwargs to not break if I add more
                    # This listener is versioned.
                    # you should not mutate the feedparser classes.
                    #
                    # version: 1
                    # destination: discord.TextChannel
                    # feed_name: str
                    # feedparser_entry: feedparser.FeedParserDict
                    # feed_settings: MappingProxy
                    # forced_update: bool
                    "sinbadcogs_rss_send",
                    listener_version=1,
                    destination=destination,
                    feed_name=feed_name,
                    feedparser_entry=entry,
                    feed_settings=MappingProxyType(feed_settings),
                    forced_update=force,
                )
            finally:
                last_sent = list(self.process_entry_time(entry))

        return last_sent

    def format_post(self, entry, embed: bool, color, template=None, roles=[]) -> dict:

        if template is None:
            if embed:
                _template = "[$title]($link)"
            else:
                _template = "$title: <$link>"
        else:
            _template = template

        template = string.Template(_template)

        data = {k: getattr(entry, k, None) for k in USABLE_FIELDS}

        def maybe_clean(key, val):
            if isinstance(val, str) and key not in DONT_HTML_SCRUB:
                return html_to_text(val)
            return val

        escaped_usable_fields = {k: maybe_clean(k, v) for k, v in data.items() if v}

        content = template.safe_substitute(**escaped_usable_fields)

        if embed:
            if len(content) > 1980:
                content = content[:1900] + "... (Feed data too long)"
            timestamp = datetime(*self.process_entry_time(entry))
            embed_data = discord.Embed(
                description=content, color=color, timestamp=timestamp
            )
            embed_data.set_footer(text="Published ")
            data = {"embed": embed_data}
            if roles:
                data["content"] = " ".join((f"<@&{rid}>" for rid in roles))
            return data
        else:
            if roles:
                mention_string = " ".join((f"<@&{rid}>" for rid in roles)) + "\n"
            else:
                mention_string = ""

            if len(content) > 1900:
                content = content[:1900] + "... (Feed data too long)"

            return {"content": mention_string + content if mention_string else content}

    async def handle_response_from_loop(
        self,
        *,
        response: Optional[feedparser.FeedParserDict],
        channel: discord.TextChannel,
        feed: dict,
        should_embed: bool,
        feed_name: str,
    ):
        if not response:
            return
        try:
            last = await self.format_and_send(
                feed_name=feed_name,
                destination=channel,
                response=response,
                feed_settings=feed,
                embed_default=should_embed,
            )
        except Exception as exc:
            debug_exc_log(log, exc)
        else:
            if last:
                await self.config.channel(channel).feeds.set_raw(
                    feed_name, "last", value=last
                )

    async def do_feeds(self):
        feeds_fetched: Dict[str, Any] = {}
        default_embed_settings: Dict[discord.Guild, bool] = {}

        channel_data = await self.config.all_channels()
        for channel_id, data in channel_data.items():

            channel = self.bot.get_channel(channel_id)
            if not channel:
                continue
            if channel.guild not in default_embed_settings:
                should_embed = await self.should_embed(channel)
                default_embed_settings[channel.guild] = should_embed
            else:
                should_embed = default_embed_settings[channel.guild]

            for feed_name, feed in data["feeds"].items():
                url = feed.get("url", None)
                if not url:
                    continue
                if url in feeds_fetched:
                    response = feeds_fetched[url]
                else:
                    response = await self.fetch_feed(url)
                    feeds_fetched[url] = response

                await self.handle_response_from_loop(
                    response=response,
                    channel=channel,
                    feed=feed,
                    feed_name=feed_name,
                    should_embed=should_embed,
                )

    async def bg_loop(self):
        await self.bot.wait_until_ready()
        while await asyncio.sleep(300, True):
            await self.do_feeds()

    # commands go here

    @checks.mod_or_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.group()
    async def rss(self, ctx: commands.GuildContext):
        """
        Configuration for rss
        """
        pass

    @commands.cooldown(5, 60, commands.BucketType.guild)
    @rss.command(name="find")
    async def find_feed_command(self, ctx: commands.Context, *, url: str):
        """
        Attempt to find feeds intelligently on a given site.

        This only works on pages that link their RSS feeds.
        """
        try:
            possible_results = await self.find_feeds(url)
        except aiohttp.ClientError as exc:
            debug_exc_log(log, exc)
            await ctx.send("Something went wrong when accessing that url.")
        else:
            output = (
                "\n".join(("Possible feeds:", *possible_results))
                if possible_results
                else "No feeds found."
            )
            for page in pagify(output):
                await ctx.send(box(page))

    @rss.command(name="force")
    async def rss_force(self, ctx, feed, channel: Optional[discord.TextChannel] = None):
        """
        Forces the latest update for a feed to post.
        """

        channel = channel or ctx.channel
        feeds = await self.config.channel(channel).feeds()
        url = None
        if feed in feeds:
            url = feeds[feed].get("url", None)

        if url is None:
            return await ctx.send("No such feed.")

        response = await self.fetch_feed(url)

        if response:
            should_embed = await self.should_embed(ctx.channel)

            try:
                await self.format_and_send(
                    feed_name=feed,
                    destination=channel,
                    response=response,
                    feed_settings=feeds[feed],
                    embed_default=should_embed,
                    force=True,
                )
            except Exception:
                await ctx.send("There was an error with that.")
            else:
                await ctx.tick()
        else:
            await ctx.send("Could not fetch feed.")

    @commands.cooldown(3, 60, type=commands.BucketType.user)
    @rss.command()
    async def addfeed(
        self,
        ctx: commands.GuildContext,
        name: str,
        url: str,
        channel: Optional[discord.TextChannel] = None,
    ):
        """
        Adds a feed to the current, or a provided channel
        """

        channel = channel or ctx.channel

        async with self.config.channel(channel).feeds() as feeds:
            if name in feeds:
                return await ctx.send("That name is already in use.")

            response = await self.fetch_feed(url)

            if response is None:
                return await ctx.send(
                    f"That didn't seem to be a valid rss feed. "
                    f"(Syntax: {ctx.prefix}{ctx.command.signature})"
                )

            else:
                feeds.update(
                    {
                        name: {
                            "url": url,
                            "template": None,
                            "embed_override": None,
                            "last": list(ctx.message.created_at.timetuple()[:6]),
                        }
                    }
                )

        await ctx.tick()

    @rss.command(name="list")
    async def list_feeds(
        self, ctx: commands.GuildContext, channel: Optional[discord.TextChannel] = None
    ):
        """
        Lists the current feeds for the current channel, or a provided one.
        """

        channel = channel or ctx.channel

        data = await self.config.channel(channel).feeds()
        if not data:
            return await ctx.send("No feeds here.")

        if await ctx.embed_requested():
            output = "\n".join(
                (
                    "{name}: {url}".format(name=k, url=v.get("url", "broken feed"))
                    for k, v in data.items()
                )
            )
            page_gen = cast(Generator[str, None, None], pagify(output))

            try:
                for page in page_gen:
                    await ctx.send(
                        embed=discord.Embed(
                            description=page, color=(await ctx.embed_color())
                        )
                    )
            finally:
                page_gen.close()

        else:
            output = "\n".join(
                (
                    "{name}: <{url}>".format(name=k, url=v.get("url", "broken feed"))
                    for k, v in data.items()
                )
            )
            page_gen = cast(Generator[str, None, None], pagify(output))
            try:
                for page in page_gen:
                    await ctx.send(page)
            finally:
                page_gen.close()

    @rss.command(name="remove")
    async def remove_feed(
        self, ctx, name: str, channel: Optional[discord.TextChannel] = None
    ):
        """
        removes a feed from the current channel, or from a provided channel

        If the feed is currently being fetched, there may still be a final update
        after this.
        """
        channel = channel or ctx.channel
        async with self.config.channel(channel).feeds() as feeds:
            if name not in feeds:
                await ctx.send(f"No feed named {name} in {channel.mention}.")
                return

            del feeds[name]

        await ctx.tick()

    @rss.command(name="embed")
    async def set_embed(
        self,
        ctx,
        name: str,
        setting: TriState,
        channel: Optional[discord.TextChannel] = None,
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

        async with self.config.channel(channel).feeds() as feeds:
            if name not in feeds:
                await ctx.send(f"No feed named {name} in {channel.mention}.")
                return

            feeds[name]["embed_override"] = setting.state

        await ctx.tick()

    @rss.command(name="template")
    async def set_template(
        self,
        ctx,
        name,
        channel: Optional[discord.TextChannel] = None,
        *,
        template: str = None,
    ):
        """
        Sets formatting for the specified feed in this, or a provided channel

        The following have special meaning based on their content in the RSS feed data.
        Any not used will remain.

        $author
        $author_detail
        $description
        $comments
        $content
        $contributors
        $updated
        $updated_parsed
        $link
        $name
        $published
        $published_parsed
        $publisher
        $publisher_detail
        $source
        $summary
        $summary_detail
        $tags
        $title
        $title_detail

        """

        if not template:
            return await ctx.send_help()

        channel = channel or ctx.channel
        template = template.replace("\\t", "\t")
        template = template.replace("\\n", "\n")
        async with self.config.channel(channel).feeds() as feeds:
            if name not in feeds:
                await ctx.send(f"No feed named {name} in {channel.mention}.")
                return

            feeds[name]["template"] = template

        await ctx.tick()

    @rss.command(name="resettemplate")
    async def reset_template(
        self, ctx, name, channel: Optional[discord.TextChannel] = None
    ):
        """
        Resets the template in use for a specific feed in this, or a provided channel
        """
        channel = channel or ctx.channel
        async with self.config.channel(channel).feeds() as feeds:
            if name not in feeds:
                await ctx.send(f"No feed named {name} in {channel.mention}.")
                return

            del feeds[name]["template"]

        await ctx.tick()

    @rss.command(
        name="matchreq", usage="<feedname> [channel] <field name> <match term>"
    )
    async def rss_set_match_req(
        self,
        ctx: commands.GuildContext,
        feed_name: str,
        channel: Optional[discord.TextChannel] = None,
        *,
        field_and_term: FieldAndTerm,
    ):
        """
        Sets a term which must appear in the given field for a feed to be published.
        """

        channel = channel or ctx.channel

        if field_and_term.field not in USABLE_TEXT_FIELDS:
            raise commands.BadArgument(
                f"Field must be one of: {', '.join(USABLE_TEXT_FIELDS)}"
            )

        async with self.config.channel(channel).feeds() as feeds:
            if feed_name not in feeds:
                await ctx.send(f"No feed named {feed_name} in {channel.mention}.")
                return

            feeds[feed_name]["match_req"] = list(field_and_term)
            await ctx.tick()

    @rss.command(name="removematchreq")
    async def feed_remove_match_req(
        self,
        ctx: commands.GuildContext,
        feed_name: str,
        channel: Optional[discord.TextChannel] = None,
    ):
        """
        Remove the reqs on a feed update.
        """

        channel = channel or ctx.channel

        async with self.config.channel(channel).feeds() as feeds:
            if feed_name not in feeds:
                await ctx.send(f"No feed named {feed_name} in {channel.mention}.")
                return

            feeds[feed_name].pop("match_req", None)
            await ctx.tick()

    @checks.admin_or_permissions(manage_guild=True)
    @rss.command(name="rolementions")
    async def feedset_mentions(
        self,
        ctx: commands.GuildContext,
        name: str,
        channel: Optional[discord.TextChannel] = None,
        *non_everyone_roles: NonEveryoneRole,
    ):
        """
        Sets the roles which are mentioned when this feed updates.

        This will clear the setting if none.
        """

        roles = set(non_everyone_roles)

        if len(roles) > 4:
            return await ctx.send(
                "I'm judging you hard here. "
                "Fix your notification roles, "
                "don't mention this many (exiting without changes)."
            )

        if roles and max(roles) > ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send(
                "I'm not letting you set a role mention for a role above your own."
            )

        channel = channel or ctx.channel
        async with self.config.channel(channel).feeds() as feeds:
            if name not in feeds:
                await ctx.send(f"No feed named {name} in {channel.mention}.")
                return

            feeds[name]["role_mentions"] = [r.id for r in roles]

        if roles:
            await ctx.send("I've set those roles to be mentioned.")
        else:
            await ctx.send("Roles won't be mentioned.")
        await ctx.tick()
