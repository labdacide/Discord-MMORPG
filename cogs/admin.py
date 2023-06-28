import discord
from discord.ext import commands
from discord.commands import slash_command, Option

import aiosqlite

from config import *
from utils import get_faction_name


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.DB = bot.db.DB

    @slash_command(description="Changes the faction of a Divergent")
    @commands.has_permissions(administrator=True)
    async def changefaction(self, ctx,
                            member: Option(discord.Member, "Specify a user"),
                            new_faction: Option(str, "The new faction", choices=FACTIONS.keys())):
        if await self.bot.db.check_faction(member) is None:
            await ctx.respond(f"{member.mention} did not choose a faction yet.", ephemeral=True)
            return

        await self.bot.db.set_faction(member, new_faction)

        for faction in FACTIONS.keys():
            role = ctx.guild.get_role(FACTIONS[faction])
            if role is None:
                await ctx.respond(f"Error: Could not find **{faction}** role", ephemeral=True)
                return

            if faction != new_faction:
                await member.remove_roles(ctx.guild.get_role(FACTIONS[faction]))
            else:
                await member.add_roles(ctx.guild.get_role(FACTIONS[faction]))

        await ctx.respond(f"{member.mention} now belongs to <@&{FACTIONS[new_faction]}>.")

    @slash_command(description="Change a faction treasury")
    @commands.has_permissions(administrator=True)
    async def treasury(
            self, ctx,
            faction: Option(str, "Choose a faction", choices=FACTIONS.keys()),
            amount: Option(int, "The amount of kcoin")
    ):
        await self.db.change_faction_value(faction, amount)
        new_bal = await self.db.get_faction_value(faction)
        f_name = get_faction_name(faction)

        await ctx.respond(
            f"You gave **{amount:,}** {CURRENCY} to {f_name}. New balance: **{new_bal:,}** {CURRENCY}."
        )

    @slash_command(description="Give stuff to a Divergent")
    @commands.has_permissions(administrator=True)
    async def admingive(
            self, ctx,
            member: Option(discord.Member, "Choose  Divergent"),
            value: Option(
                str, "Choose a value",
                choices=["coins", "xp", "lvl", "hp", "agi", "str", "men", "res", "kar"]
            ),
            amount: Option(int, "The amount of kcoins the Divergent should receive", min_value=1)
    ):
        await self.db.change_value(member, amount, value)
        new_bal = await self.db.get_value(member, value)

        await ctx.respond(
            f"You gave **{amount:,}** {value} to {member.mention}. New balance: **{new_bal:,}** {value}."
        )

    @slash_command(description="Take stuff from a Divergent")
    @commands.has_permissions(administrator=True)
    async def admintake(
            self, ctx,
            member: Option(discord.Member, "Divergent to take kcoin from"),
            value: Option(
                str, "Choose a value",
                choices=["coins", "xp", "lvl", "hp", "agi", "str", "men", "res", "kar"]
            ),
            amount: Option(int, "The amount of kcoins to take from the Divergent", min_value=1)
    ):
        bal = await self.db.get_value(member, value)
        if bal < amount:
            await ctx.respond(f"{member.mention} does only have **{bal}** {value}", ephemeral=True)
            return

        await self.db.change_value(member, 0 - amount, value)
        new_bal = await self.db.get_value(member, value)

        await ctx.respond(
            f"You took **{amount:,}** {value} from {member.mention}. New balance: **{new_bal:,}** {value}."
        )

    @slash_command(description="Show all Divergents of a faction")
    @commands.has_permissions(administrator=True)
    async def checkfaction(
            self, ctx,
            faction: Option(str, "Choose a faction", choices=FACTIONS.keys())
    ):
        desc = ""
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute("SELECT user_id FROM users WHERE faction = ?", (faction,)) as cursor:
                async for user_id in cursor:
                    desc += f"<@{user_id[0]}>\n"

        await ctx.respond(
            embed=discord.Embed(
                title=f"Divergents of {faction}",
                description=desc,
                color=COLOR
            )
        )

    @slash_command(description="Show richest Divergents")
    @commands.has_permissions(administrator=True)
    async def kcoinleaders(self, ctx):
        desc = ""
        counter = 1
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    "SELECT user_id, coins FROM users ORDER BY coins DESC LIMIT 20"
            ) as cursor:
                async for user_id, coins in cursor:
                    desc += f"`{counter}.` <@{user_id}> - **{coins:,}** {CURRENCY}\n"
                    counter += 1

        await ctx.respond(
            embed=discord.Embed(
                title=f"Kcoin leaders",
                description=desc,
                color=COLOR
            )
        )


def setup(bot):
    bot.add_cog(Admin(bot))
