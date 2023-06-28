import discord
from discord import Embed
from discord.ext import commands
from discord.commands import slash_command, Option
from discord.ext.commands import BucketType

import random
import aiosqlite
import os
from config import CURRENCY, COLOR
from utils import set_thumbnail, reset_cooldown
from utils.thx import create_milestone_reward_claim

class Actions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @slash_command(description="Earn XP")
    @commands.cooldown(1, 3 * 60 * 60, BucketType.user)  # 3 hour cooldown
    async def train(self, ctx):
        amount = random.randint(120, 210)
        await self.db.change_value(ctx.author, amount, "xp")

        new_amount = await self.db.get_value(ctx.author, "xp")
        kar = await self.db.get_value(ctx.author, "kar")

        txt = ""
        if random.randint(1, 100) in range(1, 5 + kar):
            hp = await self.db.get_value(ctx.author, "hp")
            loss = random.randint(1, 8)
            if hp - loss > 0:
                await self.db.change_value(ctx.author, -loss, "hp")
                txt = f"\n\nYou lost **{loss}** HP during the training!"

        embed = Embed(
            title="Training",
            description=f"You earned **{amount}** XP.\n\nYou now have **{new_amount:,}** XP! {txt}",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await self.check_lvl_reward(ctx.author)
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)
        code = await self.db.get_wallet_code(ctx.author)
        webhook = os.getenv("WEBHOOK_TRAIN_REWARD")
        await create_milestone_reward_claim(webhook, code)

    async def check_lvl_reward(self, author):
        _xp = await self.db.get_value(author, "xp")
        if _xp >= 1931:
            code = await self.db.get_wallet_code(author)
            webhook = os.getenv("WEBHOOK_LEVEL10_REWARD")
            await create_milestone_reward_claim(webhook, code)
        if _xp >= 14661:
            code = await self.db.get_wallet_code(author)
            webhook = os.getenv("WEBHOOK_LEVEL15_REWARD")
            await create_milestone_reward_claim(webhook, code)
        if _xp >= 111339:
            code = await self.db.get_wallet_code(author)
            webhook = os.getenv("WEBHOOK_LEVEL20_REWARD")
            await create_milestone_reward_claim(webhook, code)

    @slash_command(description="Earn Gold")
    @commands.cooldown(1, 4 * 60 * 60, BucketType.user)  # 4 hour cooldown
    async def assault(self, ctx):
        amount = random.randint(50, 200)
        await self.db.change_value(ctx.author, amount)

        new_amount = await self.db.get_value(ctx.author)
        kar = await self.db.get_value(ctx.author, "kar")

        txt = ""
        if random.randint(1, 100) in range(1, 5 + kar):
            hp = await self.db.get_value(ctx.author, "hp")
            loss = random.randint(1, 8)
            if hp - loss > 0:
                await self.db.change_value(ctx.author, -loss, "hp")
                txt = f"\n\nYou have stumbled upon a trapped ship! You lost **{loss}** HP."

        embed = Embed(
            title="Assault",
            description=f"You smashed them! You earned **{amount}** {CURRENCY}.\n\nYou now have **{new_amount:,}** {CURRENCY}! {txt}",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="A risky choice for a chance to win free gear")
    @commands.cooldown(1, 8 * 60 * 60, BucketType.user)  # 8 hour cooldown
    async def excursion(self, ctx):
        kar = await self.db.get_value(ctx.author, "kar")
        desc = ""

        rand = random.randint(1, 100)

        if rand in range(1, 30 - round(0.5*kar)):
            async with aiosqlite.connect(self.db.DB) as db:
                async with db.execute(
                        f"""SELECT id, name FROM items WHERE type = 'armor' or type = 'weapon'
                        ORDER BY RANDOM() LIMIT 1"""
                ) as cursor:
                    result = await cursor.fetchone()
                    if result is None:
                        reset_cooldown(ctx)
                        await ctx.respond("There is no gear in the database, please contact an administrator")
                        return
                    _id, name = result
                await db.execute(f"""INSERT INTO has_item (user_id, item_id) VALUES (?,?)""", (ctx.author.id, _id))
                await db.commit()
            desc += f"Business is booming! You found **{name}**!"
        elif rand in range(1, 35 + round(0.25*kar)):
            hp = await self.db.get_value(ctx.author, "hp")
            loss = random.randint(1, 10)
            if hp - loss > 0:
                await self.db.change_value(ctx.author, -loss, "hp")
                desc += f"You didn't find any gear and it seems that you got hurt on the way. You lost **{loss}** HP."
        else:
            loss = random.randint(1, 10)
            await self.db.change_value(ctx.author, -loss)
            desc += f"You didn't find any gear and you lost **{loss}** {CURRENCY} during the exploration."

        embed = Embed(
            title="Excursion",
            description=desc,
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="Restore HP and Mental")
    @commands.cooldown(1, 6 * 60 * 60, BucketType.user)  # 6 hour cooldown
    async def sleep(self, ctx):
        max_hp = await self.db.get_max_hp(ctx.author)
        cur_hp = await self.db.restore_health(ctx.author, 10)

        max_men = await self.db.get_value(ctx.author, "men")
        ment = await self.db.restore_men(ctx.author, 10)

        embed = Embed(
            title="Sleep",
            description=f"What could be better than a good nap? You earned **10%** HP and **10%** Mental!\n\n"
                        f"You now have **{cur_hp:,}/{max_hp:,}** HP and **{ment}/{max_men}** Mental.",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="Restore HP")
    @commands.cooldown(1, 3 * 60 * 60, BucketType.user)  # 3 hour cooldown
    async def potion(self, ctx):
        max_hp = await self.db.get_max_hp(ctx.author)
        cur_hp = await self.db.restore_health(ctx.author, 5)

        embed = Embed(
            title="Potion",
            description=f"""You earned **5%** HP!\n\nYou now have **{cur_hp:,} / {max_hp:,}** HP.""",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="Restore Mental")
    @commands.cooldown(1, 3 * 60 * 60, BucketType.user)  # 3 hour cooldown
    async def meditate(self, ctx):
        ment = await self.db.restore_men(ctx.author, 5)
        men = await self.db.get_value(ctx.author, "men")

        embed = Embed(
            title="Meditate",
            description=f"""You restored 5% Mental!\n\nYou now have **{ment} / {men}** Mental.""",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(embed=embed)

    @slash_command(description="Level up")
    async def levelup(self, ctx):
        if not await self.db.lvl_up_available(ctx.author):
            await ctx.respond("You need more XP to level up!", ephemeral=True)
            return

        lvl = await self.db.get_value(ctx.author, "lvl")
        if lvl == 0:
            amount = 10
        else:
            amount = 4

        embed = Embed(
            title="Level Up",
            description=f"Allocate {amount} points to level up!",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)

        await ctx.respond(embed=embed, view=LvlUpButton(ctx.author, amount, embed, self.db))

    @slash_command(description="Award a divergent that is level 0")
    async def mentor(self, ctx, member: Option(discord.Member, "Choose a divergent")):
        if ctx.author.id == member.id:
            await ctx.respond("You can't mentor yourself!", ephemeral=True)
            return
        lvl = await self.db.get_value(member, "lvl")
        if lvl != 0:
            await ctx.respond("The divergent is not level 0!", ephemeral=True)
            return

        amount = random.randint(10, 20)
        await self.db.change_value(member, amount, "xp")

        embed = Embed(
            title="Mentor",
            description=f"{ctx.author.mention} gave **{amount}** XP to {member.mention}!\n\n",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(f"{member.mention}", embed=embed, view=AcceptButton(member, ctx.author, self.db))


def setup(bot):
    bot.add_cog(Actions(bot))


class AcceptButton(discord.ui.View):
    def __init__(self, member: discord.Member, mentor, db):
        self.member = member
        self.mentor = mentor
        self.db = db
        super().__init__(timeout=None)

    async def accept(self, interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This button was created for another user!", ephemeral=True)
            return

        await self.db.change_value(self.mentor, -1, "kar")

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        embed = Embed(
            title="Level Up",
            description=f"Please, allocate 10 points to level up",
            color=COLOR
        )

        await interaction.channel.send(embed=embed, view=LvlUpButton(interaction.user, 10, embed, self.db))

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept")
    async def button_callback(self, button, interaction):
        await self.accept(interaction)


class LvlUpButton(discord.ui.View):
    def __init__(self, member: discord.Member, amount: int, embed: discord.Embed, db):
        self.member = member
        self.amount = amount
        self.embed = embed
        self.db = db
        self.counter = 0
        self.values = {"str": 0, "res": 0, "agi": 0, "men": 0}
        super().__init__(timeout=500)

    async def edit_embed(self, interaction, button):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("This button was created for another user!", ephemeral=True)
            return

        self.values[button.custom_id] += 1
        self.embed.clear_fields()

        for key, value in self.values.items():
            if value > 0:
                self.embed.add_field(name=f"{key.upper()}", value=value, inline=True)

        self.counter += 1
        if self.counter >= self.amount:
            self.embed.title = "You leveled up!"
            self.embed.description = "All points have been allocated"
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(embed=self.embed, view=self)

            if not await self.db.lvl_up_available(self.member):
                await interaction.response.send_message("You need more XP to level up!", ephemeral=True)
                return
            await self.db.change_value(self.member, self.values["str"], "str")
            await self.db.change_value(self.member, self.values["res"], "res")
            await self.db.change_value(self.member, self.values["agi"], "agi")
            await self.db.change_value(self.member, self.values["men"], "men")
            await self.db.change_value(self.member, 1, "lvl")
            await self.db.restore_health(self.member, 100)  # health is fully restored
            return

        await interaction.message.edit(embed=self.embed)

    @discord.ui.button(label="Strength", style=discord.ButtonStyle.grey, custom_id="str")
    async def button_callback1(self, button, interaction):
        await self.edit_embed(interaction, button)

    @discord.ui.button(label="Resistance", style=discord.ButtonStyle.grey, custom_id="res")
    async def button_callback2(self, button, interaction):
        await self.edit_embed(interaction, button)

    @discord.ui.button(label="Agility", style=discord.ButtonStyle.grey, custom_id="agi")
    async def button_callback3(self, button, interaction):
        await self.edit_embed(interaction, button)

    @discord.ui.button(label="Mental", style=discord.ButtonStyle.grey, custom_id="men")
    async def button_callback4(self, button, interaction):
        await self.edit_embed(interaction, button)
