import discord
import logging
from discord.ext import commands

from redbot.core import Config, RedContext
from redbot.core import checks
from redbot.core.utils.chat_formatting import pagify
from .serialize import deserialize_embed, serialize_embed
from .utils import send

log = logging.getLogger('redbot.sinbadcogs.embedmaker')


class EmbedMaker:
    """
    Storable, recallable, embed maker
    """

    __author__ = 'mikeshardmind'
    __version__ = '0.0.1a'

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160,
            force_registration=True
        )
        self.config.register_custom('EMBED', embed={}, owner=None)
        self.config.register_guild(active=True)

    @commands.group(name="embed")
    async def _embed(self, ctx: RedContext):
        """
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @commands.guild_only()
    @_embed.command(name="make")
    async def _make(self, ctx: RedContext, name: str):
        """
        makes an embed
        """
        pass

#   @_embed.command(hidden=True)
#   async def make_adv(self, ctx: RedContext, name: str, data: dict):
#       """
#       makes an embed from a dict
#       """
#       pass

    @checks.is_owner()
    @_embed.command(name='makeglobal')
    async def make_global(self, ctx: RedContext, name: str):
        """
        make a global embed
        """
        pass

#   @_embed.command(hidden=True)
#   async def make_global_adv(self, ctx: RedContext, name: str, data: dict):
#       """
#       make a global embed from a dict
#       """
#       pass

    @_embed.command(name="list")
    async def _list(self, ctx: RedContext):
        """
        lists the embeds here
        """
        embed_dict = await self.config._get_base_group('EMBED')()
        if ctx.guild:
            local_embeds = list(
                sorted(embed_dict.get(str(ctx.guild.id), {}).keys()))
        else:
            local_embeds = []

        global_embeds = list(sorted(embed_dict.get('GLOBAL', {}).keys()))

        if not local_embeds and not global_embeds:
            return await send(ctx, 'No embeds available here.')

        if local_embeds:
            local_embeds.insert(0, 'Local Embeds:')
            if global_embeds:
                local_embeds.append('\n')
        if global_embeds:
            global_embeds.insert(0, 'Global Embeds:')
        output = "\n".join(local_embeds + global_embeds)

        for page in pagify(output):
            await send(page)

    @commands.guild_only()
    @_embed.command(name="edit")
    async def _edit(self, ctx: RedContext):
        """
        edits an embed
        """
        pass

    @commands.guild_only()
    @_embed.command(name="remove")
    async def _remove(self, ctx: RedContext):
        """
        removes an embed
        """
        pass

    @checks.is_owner()
    @_embed.command(name="rmglobal")
    async def remove_global(self, ctx: RedContext):
        """
        removes a global embed
        """

    @commands.bot_has_permissions(embed_links=True)
    @_embed.command()
    async def drop(self, ctx: RedContext, name: str):
        """
        drops an embed here
        """
        try:
            x = await self.get_and_send(ctx.channel, ctx.guild.id, name)
        except (discord.Forbidden, discord.HTTPException) as e:
            log.error(e)
        else:
            if x is not None:
                await ctx.tick()

    @checks.is_owner()
    @_embed.command(name="dropglobal")
    async def drop_global(self, ctx: RedContext, name: str):
        """
        drop a global embed here
        """
        try:
            x = await self.get_and_send(ctx.channel, 'GLOBAL', name)
        except (discord.Forbidden, discord.HTTPException) as e:
            log.error(e)
        else:
            if x is not None:
                await ctx.tick()

    @commands.admin()
    @_embed.command()
    async def dm(self, ctx: RedContext, name: str, user: discord.Member):
        """
        DMs an embed
        """
        pass

    @checks.admin()
    @_embed.command()
    async def dmglobal(self, ctx: RedContext, name: str, user: discord.Member):
        """
        DMs a global embed
        """
        pass

    @checks.is_owner()
    @_embed.command(name='frommsg', hidden=True)
    async def global_from_message(self, ctx: RedContext, name: str, _id: int):
        """
        This might be made more usable later...
        """
        try:
            e = (await ctx.channel.get_message(_id)).embeds[0]
        except Exception:
            return

        await self.config.custom('EMBED', 'GLOBAL', name).embed.set(
            serialize_embed(e)
        )
        await self.config.custom('EMBED', 'GLOBAL', name).owner.set(
            ctx.author.id
        )
        await ctx.tick()

    async def get_and_send(self, where, *identifiers):
        data = await self.config.custom('EMBED', *identifiers).all()
        if data['owner'] is None:
            return None
        embed = deserialize_embed(data['embed'])
        await where.send(embed=embed)
