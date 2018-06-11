import discord
import re
from discord.ext import commands


def role_mention_cleanup(message: discord.Message) -> str:

    if message.guild is None:
        return message.content

    transformations = {
        re.escape("<@&{0.id}>".format(role)): "@" + role.name
        for role in message.role_mentions
    }

    def repl(obj):
        return transformations.get(re.escape(obj.group(0)), "")

    pattern = re.compile("|".join(transformations.keys()))
    result = pattern.sub(repl, message.content)

    return result


def embed_from_msg(message: discord.Message) -> discord.Embed:
    channel = message.channel
    guild = channel.guild
    content = role_mention_cleanup(message)
    author = message.author
    sname = guild.name
    cname = channel.name
    avatar = author.avatar_url
    footer = f"Said in {guild.name} #{channel.name}"
    color = author.color if author.color.value != 0 else discord.Embed.Empty
    em = discord.Embed(description=content, color=color, timestamp=message.created_at)
    em.set_author(name=f"{author.name}", icon_url=avatar)
    em.set_footer(icon_url=guild.icon_url, text=footer)
    if message.attachments:
        a = message.attachments[0]
        fname = a.filename
        url = a.url
        if fname.split(".")[-1] in ["png", "jpg", "gif", "jpeg"]:
            em.set_image(url=url)
        else:
            em.add_field(
                name="Message has an attachment",
                value=f"[{fname}]({url})",
                inline=True,
            )
    return em


async def eligible_channels(ctx: commands.Context) -> list:
    """
    Get's the eligible channels to check
    """

    ret = []
    is_owner = await ctx.bot.is_owner(ctx.author)
    needed_perms = discord.Permissions()
    needed_perms.read_messages = True
    needed_perms.read_message_history = True
    guild_order = [g for g in ctx.bot.guilds if g != ctx.guild]
    if ctx.guild:
        guild_order.insert(0, ctx.guild)

    for g in ctx.bot.guilds:
        chans = [
            c
            for c in g.text_channels
            if c.permissions_for(g.me) >= needed_perms
            and (is_owner or c.permissions_for(ctx.author) >= needed_perms)
        ]
        if ctx.channel in chans:
            chans.remove(ctx.channel)
            chans.insert(0, ctx.channel)

        ret.extend(chans)

    return ret


async def find_msg(ctx: commands.Context, idx: int) -> discord.Message:

    for channel in await eligible_channels(ctx):
        try:
            m = await channel.get_message(idx)
        except Exception:
            continue
        else:
            return m
