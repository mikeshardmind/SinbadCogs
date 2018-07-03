import discord
from redbot.core.config import Config
from redbot.core import commands, checks
from .converters import (
    ProfessionConverter,
    ProfessionLevelConverter,
    MultiProfConverter,
    valid_profs,
)


class ProfBox:
    """
    Custom solution for in game profession discovery
    """

    __author__ = "mikeshardmind(Sinbad#0001)"
    __version__ = "1.0.1"

    default_guild = {k: {} for k in valid_profs}

    def __init__(self):
        self.config = Config.get_conf(
            self, identifier=78631113035100160, force_registration=True
        )
        self.config.register_guild(**self.default_guild)

    def wip(**kwargs):
        """
        Check wrapper for hiding stuff in a way manipulateable with dev tools
        """

        def pred(ctx):
            return False

        return commands.check(pred)

    @commands.guild_only()
    @commands.group(autohelp=True, name="prof")
    async def _group(self, ctx: commands.Context):
        """
        Commands for the prof box
        """
        pass

    @_group.command()
    async def register(
        self,
        ctx: commands.Context,
        profession: ProfessionConverter,
        level: ProfessionLevelConverter,
    ):
        """
        Register yourself as having a specific profession level
        """

        cfg = getattr(self.config.guild(ctx.guild), profession)

        async with cfg() as guild_prof_data:
            guild_prof_data.update({str(ctx.author.id): level})
        await ctx.tick()

    @wip()
    @_group.command(name="setign")
    async def setign(self, ctx: commands.Context, *igns: str):
        """
        Set one or more IGNs as yours.

        This will be displayed to other users looking for your profs.
        """

        await self.config.member(ctx.author).igns.set(list(igns))
        if len(igns) == 0:
            await ctx.send("Your IGNs have been cleared.")
        else:
            await ctx.send("Your IGNs have been stored.")

    @_group.command(name="multiregister")
    async def multiregister(
        self, ctx: commands.Context, *, profession_list: MultiProfConverter
    ):
        """
        Register multiple professions quickly
        """
        for prof, level in profession_list.items():
            cfg = getattr(self.config.guild(ctx.guild), prof)
            async with cfg() as guild_prof_data:
                guild_prof_data.update({str(ctx.author.id): level})

        await ctx.tick()

    @_group.command(name="find")
    async def findprof(
        self,
        ctx: commands.Context,
        profession: ProfessionConverter,
        level: ProfessionLevelConverter,
    ):
        """
        Find people with the specified profession & level

        Default ordering priority (of matches)
        1. Playing Dofus
        2. Online -> Away -> Streaming -> DND -> Offline
        3. Lowest listed level -> Highest
        """
        status_prio = {"online": 1, "idle": 2, "dnd": 4, "offline": 5}
        matches = []
        cfg = getattr(self.config.guild(ctx.guild), prof)
        async with cfg() as guild_prof_data:
            for _id, mlevel in pdata[profession].items():
                member = ctx.guild.get_member(int(_id))
                if member is None or mlevel < level:
                    continue

                if user.activity is None:
                    priority = status_prio.get(user.status.value, 6)
                elif (
                    user.activity.type == discord.ActivityType.playing
                    and "dofus" in user.activity.name.lower()
                ):
                    priority = 0
                elif user.activity.type == discord.ActivityType.streaming:
                    priority = 3
                else:
                    priority = 6

                matches.append((priority, mlevel, member))

        if not matches:
            return await ctx.send("No matches.")

        matches = sorted(matches)

        title = f"Matches for level {level} {profession}"

        body = "\n".join(
            "{member.mention} : Level {level}".format(member=x[2], level=x[1])
            for x in matches
        )

        embed = discord.Embed(
            color=(ctx.guild.me.color or discord.Embed.Empty), description=body
        )
        embed.set_author(text=title)
        embed.add_field(
            title="Disclaimer",
            value=(
                "This is only a list of who have signed up, "
                "be considerate of people's time and discord status when "
                "using this tool to find a professional."
                "\nDespite the appearance of the embed, none of these are actually mentions."
            ),
        )
        await ctx.send(embed=embed)
