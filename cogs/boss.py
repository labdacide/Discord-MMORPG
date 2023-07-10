import discord
from discord import Embed
from discord.ext import commands
from discord.commands import slash_command, Option

import aiosqlite
import random
import asyncio

from config import COLOR, CURRENCY

# BOSS_DB = Database.DB

class Boss(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.DB = bot.db.DB

    @commands.Cog.listener()
    async def on_ready(self):
        await self.setup_db()

    async def setup_db(self):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS boss (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    image TEXT,
                    hp INTEGER DEFAULT 0,
                    current_hp INTEGER DEFAULT 0
                )"""
            )
            await db.execute(
                """CREATE TABLE IF NOT EXISTS boss_attackers (
                    boss_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    damage INTEGER NOT NULL,
                    FOREIGN KEY (boss_id) REFERENCES boss (id)
                )"""
            )
            await db.commit()

    async def get_items(self):
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute("SELECT name FROM items") as cursor:
                async for name in cursor:
                    items.append(name[0])
        return items

    @slash_command(description="Create a boss")
    @commands.has_permissions(administrator=True)
    async def create_boss(
            self, ctx,
            name: Option(str, "Name of the boss"),
            image: Option(discord.Attachment, "Boss picture"),
            hp: Option(int, "Set the boss HP", min_value=1),
    ):
        boss_exists = await self.db.check_boss_exists()
        if boss_exists:
            await ctx.respond("A boss is already active. Please wait until the current boss is defeated.", ephemeral=True)
            return

        await self.db.create_boss(name, image.url if image else None, hp)
        boss_id = await self.db.get_boss_id()
        await ctx.respond(f"Boss **{name}** created with HP: **{hp}**", ephemeral=True)

    async def boss_battle(self, ctx, boss_id):
        boss_info = await self.db.get_boss_info(boss_id)
        if not boss_info:
            return

        await ctx.send(f"The boss '{boss_info['name']}' has appeared with {boss_info['current_hp']} HP!")

        while boss_info['current_hp'] > 0:
            # Wait for users to attack the boss
            try:
                attack_msg = await self.bot.wait_for('message', check=lambda m: m.author != self.bot.user, timeout=60)
                attacker = attack_msg.author
                damage = random.randint(10, 20)  # Generate a random damage value
                boss_info['current_hp'] -= damage

                if boss_info['current_hp'] <= 0:
                    boss_info['current_hp'] = 0
                    break

                await self.db.add_boss_attacker(boss_id, attacker.id, damage)

                await ctx.send(f"{attacker.mention} dealt {damage} damage to the boss '{boss_info['name']}'!")
                await ctx.send(f"The boss '{boss_info['name']}' now has {boss_info['current_hp']} HP remaining.")
            except asyncio.TimeoutError:
                await ctx.send("The boss battle has ended due to inactivity.")
                return

        await ctx.send(f"The boss '{boss_info['name']}' has been defeated!")
        await self.reward_attackers(ctx, boss_id)

        # Cleanup boss data
        await self.db.reset_boss_info(boss_id)
    
    @slash_command(description="Attack the boss")
    async def attack_boss(self, ctx):
        await ctx.send("Attack boss")

    async def reward_attackers(self, ctx, boss_id):
        boss_info = await self.db.get_boss_info(boss_id)
        if not boss_info:
            return

        reward = random.randint(100, 200)  # Generate a random reward value
        attackers = await self.db.get_boss_attackers(boss_id)

        if len(attackers) > 0:
            reward_per_attacker = reward // len(attackers)
            for attacker in attackers:
                # Give rewards to each attacker
                # Replace this with your own reward system
                await self.db.give_currency(attacker, reward_per_attacker)

            await ctx.send(f"The boss '{boss_info['name']}' has been defeated! Attackers have received rewards.")
        else:
            await ctx.send(f"The boss '{boss_info['name']}' has been defeated, but no one participated.")
    
    @slash_command(description="View the boss")
    async def view_boss(self, ctx):
        boss_info = await self.db.get_boss_info()
        if not boss_info:
            return

        embed = Embed(
            title=f"{boss_info['name']} Boss",
            description=f"HP: {boss_info['current_hp']}/{boss_info['hp']}",
            color=COLOR
        )
        embed.set_image(url=boss_info['image'])
        await ctx.send(embed=embed)

    @slash_command(description="Clear the boss")
    @commands.has_permissions(administrator=True)
    async def clear_boss(self, ctx):
        await self.db.clean_all_boss()
        await ctx.send("Boss cleared.")
def setup(bot):
    bot.add_cog(Boss(bot))
