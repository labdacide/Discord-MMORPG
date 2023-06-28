import discord
from discord import Embed
from discord.ext import commands
from discord.commands import slash_command, Option

import aiosqlite
import os

from config import COLOR, CURRENCY
from utils import set_thumbnail, get_faction_name
from cogs.shop import Shop


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.DB = bot.db.DB

    @slash_command(description="Show information about your Divergent")
    async def divergent(
            self, ctx,
            member: Option(discord.Member, "A Divergent of this server", required=False, default=None)
    ):
        if member is None:
            member = ctx.author

        hp = await self.db.get_value(member, "hp")
        max_hp = await self.db.get_max_hp(member)
        faction = await self.db.check_faction(member)

        armor = await Shop.get_equipped_armor(member)
        weapon = await Shop.get_equipped_weapon(member)

        _str, res, agi, men, ment = await self.db.get_base_stats(member)
        dmg, cel, cr, dr = await self.db.get_combat_stats(member)
        lvl, xp, kar, kills = await self.db.get_sec_stats(member)
        pow_lvl = await self.db.get_pow_lvl(member)

        stat_reveal = await self.db.check_item(ctx.author, "stats")
        await self.db.use_item(ctx.author, "stats")
        can_lvl_up = await self.db.lvl_up_available(member)
        lvl_up_txt = "*(level up available)*" if can_lvl_up else ""


        embed = Embed(
            title="Human Divergence",
            description=f"Hey {member.mention}, your avatar has the following stats.",
            color=COLOR
        )
        set_thumbnail(member, embed)

        embed.add_field(name="Power Level", value=f"{pow_lvl:,}")
        if faction is not None:
            f_name = get_faction_name(faction)
            embed.add_field(name="Faction", value=f_name)

        if ctx.author.guild_permissions.administrator or ctx.author.id == member.id or stat_reveal:
            embed.add_field(name="HP", value=f"{hp}/{max_hp}")
            embed.add_field(name="Strength", value=_str)
            embed.add_field(name="Resistance", value=res)
            embed.add_field(name="Agility", value=agi)
            embed.add_field(name="Mental", value=f"{ment}/{men}")
            embed.add_field(name="Level", value=f"{lvl_up_txt}\n{lvl}")
            embed.add_field(name="XP", value=f"{xp:,}")
            embed.add_field(
                name="Combat",
                value=f"Damage: `{dmg}`\nInitiative: `{cel}`\nKills: `{kills}`\n"
                      f"Critical Rate: `{round(cr, 1)}%`\nDodge Rate: `{round(dr, 1)}%`"
            )
            embed.add_field(
                name="Active Gears",
                value=f"Weapon:`{weapon}`\nArmor: `{armor}`\n")
            embed.add_field(name="Karma", value=kar)

        if stat_reveal:
            coins = await self.db.get_value(member)
            embed.add_field(name=f"{CURRENCY.capitalize()}", value=coins)
            embed.add_field(name="Items", value=await Shop.get_inventory_string(self, member))

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="Show your ranking")
    async def ranking(self, ctx):
        pow_lvl = await self.db.get_pow_lvl(ctx.author)
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""SELECT COUNT(*) FROM users WHERE {self.db.get_power_level_sql()} > ?""",
                    (pow_lvl,)) as cursor:
                rank = (await cursor.fetchone())[0]
            async with db.execute("""SELECT COUNT(*) FROM users""") as cursor:
                total = (await cursor.fetchone())[0]

        embed = Embed(title="Ranking",
                      description=f"""
                      Your power level is **{pow_lvl:,}**.\n
                      You are rank **{rank + 1:,} / {total:,}** in the main leaderboard.""",
                      color=COLOR)
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="Show your ranking")
    async def mainleaderboard(self, ctx):
        leaderboard = ""
        counter = 1

        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""SELECT user_id, faction, {self.db.get_power_level_sql()} FROM users 
                    ORDER BY {self.db.get_power_level_sql()} DESC LIMIT 20""") as cursor:
                async for user_id, faction, pow_lvl in cursor:
                    leaderboard += f"`{counter}.` <@{user_id}> - {round(pow_lvl):,} - {faction}\n"
                    counter += 1

        embed = Embed(
            title="Main Leaderboard",
            description=leaderboard,
            color=COLOR
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(embed=embed)

    @slash_command(description="Show your balance")
    async def balance(self, ctx, member: Option(discord.Member, "Choose a Divergent", required=False, default=None)):
        if member is None:
            member = ctx.author
        elif not ctx.author.guild_permissions.administrator:
            await ctx.respond("You don't have permission to see this", ephemeral=True)
            return

        coins = await self.db.get_value(member)

        embed = Embed(title="Balance",
                      description=f"""{member.mention} has **{coins:,}** kcoins.""",
                      color=COLOR)
        set_thumbnail(member, embed)
        await ctx.respond(embed=embed, ephemeral=True)

    async def get_faction_score(self, faction):
        total = 0
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""SELECT {self.db.get_power_level_sql()} FROM users WHERE faction = ?""", (faction,)
            ) as cursor:
                async for pow_lvl in cursor:
                    total += pow_lvl[0]

            async with db.execute(f"SELECT COUNT(*) FROM users WHERE faction = ?", (faction,)) as cur:
                member_count = (await cur.fetchone())[0]

            async with db.execute(f"SELECT coins FROM factions WHERE faction = ?", (faction,)) as cur:
                treasury = (await cur.fetchone())[0]

        return {"name": get_faction_name(faction), "power": total, "member_count": member_count, "treasury": treasury}

    @slash_command(description="Show the faction leaderboard")
    async def factionleaderboard(self, ctx):
        def sort_key(e):
            return e["power"]

        mars = await self.get_faction_score("mars")
        uranus = await self.get_faction_score("uranus")
        jupiter = await self.get_faction_score("jupiter")
        venus = await self.get_faction_score("venus")
        neptune = await self.get_faction_score("neptune")

        factions = [mars,uranus,jupiter,venus,neptune]
        factions.sort(key=sort_key, reverse=True)

        embed = Embed(title="Faction Leaderboard", color=COLOR)
        for index, faction in enumerate(factions):
            power = round(faction['power'])
            embed.add_field(
                name=f"`{index + 1}.` {faction['name']}",
                value=f"- Faction Power: **{power:,}**\n"
                      f"- Members: **{faction['member_count']}**\n"
                      f"- Treasury: **{faction['treasury']:,}** {CURRENCY}",
                inline=False
            )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(embed=embed)

    @slash_command(description="Show the help menu")
    async def gamehelp(self, ctx):
        excluded_cmds = ["additem", "removeitem"]
        excluded_cogs = ["admin", "reactionroles"]
        embed = Embed(
            title="Game Help",
            color=COLOR
        )

        for cog_name, cog in zip(self.bot.cogs.keys(), self.bot.cogs.values()):
            if cog_name.lower() in excluded_cogs:
                continue
            for command in cog.walk_commands():
                if command.name in excluded_cmds:
                    continue
                embed.add_field(name=f"/{command.name}", value=f"```{command.description}```")

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="Get your THX Reward")
    async def thxreward(self, ctx):
        code = await self.db.get_wallet_code(ctx.author)
        await ctx.respond(ephemeral=True, view=SimpleButton(code))

def setup(bot):
    bot.add_cog(Information(bot))

class SimpleButton(discord.ui.View):
    def __init__(self, code):
        super().__init__(timeout=None)
        button = discord.ui.Button(label='Complete Quest', style=discord.ButtonStyle.url, url=os.getenv("THX_PREVIEW") + code)
        self.add_item(button)