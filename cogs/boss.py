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
                    str INTEGER DEFAULT 1,
                    res INTEGER DEFAULT 1,
                    hp INTEGER DEFAULT 0,
                    current_hp INTEGER DEFAULT 0,
                    time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    @slash_command(description="Create a boss")
    @commands.has_permissions(administrator=True)
    async def create_boss(
            self, ctx,
            name: Option(str, "Name of the boss"),
            image: Option(discord.Attachment, "Boss picture"),
            strength: Option(int, "Set the boss strength", min_value=1),
            resistance: Option(int, "Set the boss resistance", min_value=1),
            hp: Option(int, "Set the boss HP", min_value=1),
            time: Option(str, "Time of boss creation (YYYY-MM-DD HH:MM:SS e.g. 2023-01-01 12:00:00)")
    ):
        boss_exists = await self.db.check_boss_exists()
        if boss_exists:
            await ctx.respond("A boss is already active. Please wait until the current boss is defeated.", ephemeral=True)
            return


        await self.db.create_boss(name, image.url if image else None, strength, resistance, hp, time)
        # boss_id = await self.db.get_boss_id()
        await ctx.respond(f"Boss **{name}** created with HP: **{hp}**", ephemeral=True)

    async def boss_battle(self, ctx, boss_id):
        boss_info = await self.db.get_boss_info(boss_id)
        if not boss_info:
            return

        await ctx.send(f"The boss '{boss_info['name']}' has appeared with {boss_info['current_hp']} HP!")

        # Wait for one user to attack the boss
        try:
            attack_msg = await self.bot.wait_for('message', check=lambda m: m.author != self.bot.user, timeout=60)
            attacker = attack_msg.author
            damage = random.randint(10, 20)  # Generate a random damage value
            boss_info['current_hp'] -= damage

            if boss_info['current_hp'] <= 0:
                boss_info['current_hp'] = 0
                await ctx.send(f"The boss '{boss_info['name']}' has been defeated!")
                await self.reward_attackers(ctx, boss_id)
                await self.db.reset_boss_info(boss_id)
            else:
                await ctx.send(f"{attacker.mention} dealt {damage} damage to the boss '{boss_info['name']}'!")
                await ctx.send(f"The boss '{boss_info['name']}' now has {boss_info['current_hp']} HP remaining.")
        except asyncio.TimeoutError:
            await ctx.send("The boss battle has ended due to inactivity.")


    @slash_command(description="Attack the boss")
    async def attack_boss(self, ctx):
        boss_id = await self.db.get_boss_id()
        if not boss_id:
            await ctx.respond("There is no active boss to attack.", ephemeral=True)
            return
        
        # Check if the user has already attacked the boss
        attacker_id = ctx.author.id
        if await self.db.is_attacker(boss_id, attacker_id):
            await ctx.respond("You have already attacked the boss. Please wait for others to take their turn.", ephemeral=True)
            return
        
        # Perform the attack logic here
        # ...
        # Update the boss HP in the database
        await self.db.update_boss_hp(boss_id)

        # Check if the boss is defeated
        if boss_info["hp"] <= 0:
            # Calculate rewards for all users who attacked the boss
            rewards = calculate_rewards(ctx.author, boss_info["damage"])

            # Distribute rewards to the users
            await distribute_rewards(rewards)

            # Reset the boss information in the database
            await self.db.reset_boss_info()

            await ctx.respond("Congratulations! The boss has been defeated. You received rewards.", ephemeral=True)
        else:
            await ctx.respond("You attacked the boss. Keep fighting!", ephemeral=True)


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

    @slash_command(description="Clear the boss table")
    @commands.has_permissions(administrator=True)
    async def clear_boss_table(self, ctx):
        await self.db.delete_boss_tables()
        await ctx.send("Boss table cleared.")

def setup(bot):
    bot.add_cog(Boss(bot))
