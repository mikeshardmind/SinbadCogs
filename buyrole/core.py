import math
import asyncio
import discord
from redbot.core import Config, bank, commands, checks
from redbot.core.utils.menus import start_adding_reactions, menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import pagify, box


REACTIONS = {"\N{WHITE HEAVY CHECK MARK}": True, "\N{CROSS MARK}": False}


class BuyRole(commands.Cog):
    """
    A simple purchasable role cog
    """

    __version__ = "1.0.3"

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_role(cost=0)

    @checks.bot_has_permissions(manage_roles=True)
    @checks.admin_or_permissions(manage_roles=True)
    @commands.guild_only()
    @commands.group()
    async def buyroleset(self, ctx: commands.Context):
        """ Configuration for buyrole """
        pass

    @buyroleset.command()
    async def cost(self, ctx: commands.Context, cost: int, *, role: discord.Role):
        """
        Sets the cost of a role.

        Setting a cost to zero will make it non-purchasable
        """

        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            return await ctx.send("You can't set the cost for a role")

        if role >= ctx.me.top_role and ctx.me != ctx.guild.owner:
            await ctx.send("Warning: I can't give out this role currently.")

        if cost < 0:
            return await ctx.send(
                "The cost needs to be a positive number (or zero to set as non-purchaseable)"
            )

        await self.config.role(role).cost.set(cost)
        if cost == 0:
            await ctx.send("Role no longer purchasable.")
        else:
            await ctx.send(f"Role is purchasable for {cost}")

    @commands.guild_only()
    @commands.command()
    async def roleprices(self, ctx: commands.Context):
        """
        Shows prices of roles
        """

        rdata = await self.config.all_roles()
        inf = []
        mxwidth = 4  # "Cost"
        for role in ctx.guild.roles:
            if role.id in rdata:
                cost = rdata[role.id]["cost"]
                if cost:
                    mxwidth = max(mxwidth, int(math.log10(cost)) + 1)
                    inf.append((cost, role.name))

        inf.sort()
        inf.insert(0, (f"{'Cost': <{mxwidth}}", "Role"))
        output = "\n".join(f"{c: >{mxwidth}} {r}" for c, r in inf)

        if len(output) <= 1992:
            await ctx.send(box(output))
        else:
            pages = [box(p) for p in pagify(output)]
            await menu(ctx, pages, DEFAULT_CONTROLS)

    @commands.guild_only()
    @checks.bot_has_permissions(manage_roles=True, add_reactions=True)
    @commands.command()
    async def buyrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Buy a role. 
        
        you can view purchasable roles using `[p]roleprices`
        """
        if role >= ctx.me.top_role and ctx.me != ctx.guild.owner:
            return  # Can't give this role

        cost = await self.config.role(role).cost()
        if cost < 1:
            return  # Role Not for sale.

        if role in ctx.author.roles:
            return await ctx.send("You already have that role!")

        currency = await bank.get_currency_name(ctx.guild)

        m = await ctx.send(
            f"This will cost you {cost} {currency}. Do you want to spend it?"
        )
        start_adding_reactions(m, REACTIONS.keys())

        try:

            def predicate(r, u):
                return u == ctx.author and r.message.id == m.id and r.emoji in REACTIONS

            react, _user = await ctx.bot.wait_for(
                "reaction_add", check=predicate, timeout=30
            )
        except asyncio.TimeoutError:
            return await ctx.send("I can't wait forever.")

        confirm = REACTIONS[react.emoji]

        if confirm:
            try:
                await bank.withdraw_credits(ctx.author, cost)
            except ValueError:
                return await ctx.send(f"You don't have enough {currency}!")

            try:
                await ctx.author.add_roles(role, reason="Role purchase")
            except discord.HTTPException:
                await bank.deposit_credits(ctx.author, cost)
                await ctx.send(
                    "I couldn't give you that role due to an unexpected error"
                )
            else:
                await ctx.send(f"You purchased {role} for {cost} {currency}.")

        else:
            await ctx.send("Okay, you don't have to buy it.")
