import discord
from discord import Embed
from discord.ext import commands, tasks
from discord.commands import slash_command, Option
from discord.ext.commands import BucketType

import random
import asyncio
import aiosqlite
from datetime import time, timezone

from config import COLOR, FACTIONS, CURRENCY
from utils import *

a_members = []
d_members = []

battle = {}


class Combat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.DB = bot.db.DB

    @commands.Cog.listener()
    async def on_ready(self):
        self.restore_hp.start()

    @tasks.loop(
        time=time(7, 0, tzinfo=timezone.utc)
    )
    async def restore_hp(self):
        print(f"[{discord.utils.utcnow()}] Restoring HP")

        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"SELECT user_id, res, hp FROM users") as cursor:
                for user_id, res, hp in await cursor.fetchall():
                    try:
                        member = await self.bot.fetch_user(user_id)
                    except discord.NotFound:
                        continue
                    max_hp = await self.db.get_max_hp(member)
                    if hp + max_hp * 0.5 >= max_hp:
                        new_hp = max_hp
                    else:
                        new_hp = hp + max_hp * 0.5

                    await self.db.set_value(member, new_hp, "hp")

    @slash_command(description="Ambush a player")
    @commands.cooldown(1, 30 * 60, BucketType.user)  # 30 min cooldown
    async def ambush(self, ctx, member: Option(discord.Member, "The Divergent you want to ambush")):
        attacker = ctx.author
        defender = member
        if member.bot or attacker.id == defender.id:
            reset_cooldown(ctx)
            await ctx.respond("You can't ambush yourself or a bot!", ephemeral=True)
            return

        a_hp = await self.db.get_value(attacker, "hp")
        d_hp = await self.db.get_value(defender, "hp")
        d_lvl = await self.db.get_value(defender, "lvl")
        if a_hp <= 0:
            reset_cooldown(ctx)
            await ctx.respond("You need more HP!", ephemeral=True)
            return
        if d_hp <= 0:
            reset_cooldown(ctx)
            await ctx.respond("Your opponent does not have enough HP!", ephemeral=True)
            return
        if d_lvl <= 1:
            reset_cooldown(ctx)
            await ctx.respond("Your opponent's level is too low!", ephemeral=True)
            return

        # karma
        a_lvl = await self.db.get_value(attacker, "lvl")
        if d_lvl + 5 < a_lvl:
            await self.db.change_value(attacker, 1, "kar")

        # check items
        trap = await self.db.check_item(defender, "trap")
        shield = await self.db.check_item(defender, "shield")
        if trap:
            await self.db.use_item(defender, "trap")
            await ctx.respond(
                embed=Embed(
                    title="Trap",
                    description=f"{attacker.mention} was caught by a trap and died!",
                    color=COLOR
                )
            )
            await self.db.set_value(attacker, 0, "hp")
            await self.db.death(attacker, defender, ctx.channel)
            return
        if shield:
            await ctx.respond("The user has a shield!", ephemeral=True)
            return

        kar = round(await self.db.get_value(attacker, "kar"))
        if random.randint(1, 100) in range(1, kar):
            await self.db.set_value(attacker, 0, "hp")
            await ctx.respond("You died spontaneously because of your Karma!")
            await self.db.death(attacker, defender, ctx.channel)
            return

        a_agi = await self.db.get_value(attacker, "agi")
        d_agi = await self.db.get_value(defender, "agi")
        a_dmg, _, _, _ = await self.db.get_combat_stats(attacker)
        d_dmg, _, _, _ = await self.db.get_combat_stats(defender)

        success_chance = 55 + (a_agi / 2 - d_agi / 2)

        if random.randint(1, 100) <= success_chance:  # ambush successful
            attacker_won = True
            dmg = round(1.5 * a_dmg)
            await self.db.change_value(attacker, 2*get_winner_xp(), "xp")
            await self.db.change_value(defender, -dmg, "hp")

            new_hp = await self.db.get_value(defender, "hp")
            if new_hp <= 0:
                death_txt = f"\n\n{defender.mention} died, but can be revived for a short time."
                await self.db.change_value(attacker, 1, "kills")
            else:
                death_txt = f"\n\n{defender.mention}has **{new_hp} HP** left."

            await self.db.use_gear(attacker, "weapon")
            await self.db.use_gear(defender, "armor")

            embed = Embed(
                title="Ambush successful!",
                description=f"""{attacker.mention} dealt **{dmg}** damage to {defender.mention}.{death_txt}""",
                color=COLOR
            )
            set_thumbnail(attacker, embed)
        else:  # ambush failed
            attacker_won = False
            dmg = round(2 * d_dmg)
            await self.db.change_value(defender, 2*get_winner_xp(), "xp")
            await self.db.change_value(attacker, -dmg, "hp")

            new_hp = await self.db.get_value(attacker, "hp")
            if new_hp <= 0:
                death_txt = f"\n\n{attacker.mention} died, but can be revived for a short time."
                await self.db.change_value(defender, 1, "kills")
            else:
                death_txt = f"\n\n{attacker.mention}has **{new_hp} HP** left."

            await self.db.use_gear(attacker, "armor")
            await self.db.use_gear(defender, "weapon")

            embed = Embed(
                title="Ambush defended!",
                description=f"""{defender.mention} dealt **{dmg}** damage to {attacker.mention}.{death_txt}""",
                color=COLOR
            )
            set_thumbnail(defender, embed)

        await ctx.respond(f"{defender.mention}", embed=embed)

        if new_hp > 0:
            return
        if attacker_won:
            await self.db.death(defender, attacker, ctx.channel)
        else:
            await self.db.death(attacker, defender, ctx.channel)

    @slash_command(description="Challenge someone to a duel")
    @commands.cooldown(1, 3 * 60, BucketType.user)  # 3 min cooldown
    async def duel(self, ctx, member: Option(discord.Member, "The Divergent you want to fight")):
        attacker = ctx.author
        defender = member

        a_hp = await self.db.get_value(attacker, "hp")
        d_hp = await self.db.get_value(defender, "hp")
        if a_hp <= 0:
            reset_cooldown(ctx)
            await ctx.respond("You need more HP!", ephemeral=True)
            return
        if d_hp <= 0:
            reset_cooldown(ctx)
            await ctx.respond("Your opponent does not have enough HP!", ephemeral=True)
            return
        if attacker.id == defender.id:
            reset_cooldown(ctx)
            await ctx.respond("You can't duel yourself!", ephemeral=True)
            return

        kar = round(await self.db.get_value(attacker, "kar"))
        if random.randint(1, 100) in range(1, kar):
            await self.db.set_value(attacker, 0, "hp")
            await ctx.respond("You died spontaneously because of your Karma!")
            await self.db.death(attacker, defender, ctx.channel)
            return

        embed = Embed(
            title="Duel",
            description=f"{attacker.mention} challenges {defender.mention} to a duel.",
            color=COLOR
        )
        set_thumbnail(attacker, embed)

        await ctx.respond(
            f"{defender.mention}",
            embed=embed,
            view=AcceptRefuseButton(attacker, defender, self.bot.db)
        )

    @slash_command(description="Revive a wounded ally")
    @commands.cooldown(1, 3 * 60, BucketType.user)  # 3 min cooldown
    async def revive(self, ctx, member: Option(discord.Member, "The Divergent you want to revive")):
        if ctx.author.id == member.id:
            reset_cooldown(ctx)
            await ctx.respond("You can't revive yourself!", ephemeral=True)
            return
        hp = await self.db.get_value(member, "hp")
        if hp > 0:
            reset_cooldown(ctx)
            await ctx.respond(f"{member.mention} is not dead!", ephemeral=True)
            return

        await self.db.set_value(member, 5, "hp")
        await self.db.change_value(ctx.author, random.randint(20, 50), "xp")

        embed = Embed(
            title="Revive",
            description=f"You revived {member.mention}!",
            color=COLOR
        )
        set_thumbnail(member, embed)
        await ctx.respond(f"{member.mention}", embed=embed)

    @slash_command(description="Escape from a duel")
    async def escape(self, ctx):
        if ctx.author.id not in battle or not battle[ctx.author.id]:
            await ctx.respond("You are not in a duel!", ephemeral=True)
            return

        if random.randint(1, 100) in range(1, 90):  # escape successful
            battle[ctx.author.id] = False

            if random.randint(1, 100) in range(1, 90):
                loss_txt = f"\n\n{ctx.author.mention} did not lose any kcoin!"
            else:
                a_coins = await self.db.get_value(ctx.author)
                coins_lost = round(a_coins * 0.2)
                await self.db.change_value(ctx.author, -coins_lost)
                loss_txt = f"\n\n{ctx.author.mention} lost **{coins_lost}** kcoins during the escape!"

            await ctx.respond(
                embed=Embed(
                    title="Escape",
                    description=f"{ctx.author.mention} escaped the duel successfully! {loss_txt}",
                    color=COLOR
                )
            )

        else:  # escape failed
            await ctx.respond(f"{ctx.author.mention} could not escape. Keep dueling!")

    @slash_command(description="Raid a faction")
    @commands.cooldown(1, 1 * 60 * 60, BucketType.guild)
    async def factionraid(
            self, ctx,
            faction: Option(str, "The faction you want to raid", choices=FACTIONS.keys())
    ):
        def clear():
            a_members.clear()
            d_members.clear()

        clear()
        d_faction = faction

        a_faction = await self.db.check_faction(ctx.author)
        if a_faction is None:
            reset_cooldown(ctx)
            await ctx.respond("You must choose a faction first!", ephemeral=True)
            return
        if a_faction == d_faction:
            reset_cooldown(ctx)
            await ctx.respond("You can't raid your own faction, that's not nice!", ephemeral=True)
            return
        a_name = get_faction_name(a_faction)
        d_name = get_faction_name(d_faction)

        embed = Embed(
            title="Faction Raid",
            description=f"""{ctx.author.mention} wants to raid **{d_name}**! 
            \nClick below to join.""",
            color=COLOR
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(f"<@&{FACTIONS[a_faction]}>", embed=embed, view=FactionRaidButton(a_faction, self.db))
        await asyncio.sleep(600)

        if len(a_members) < 6:
            await ctx.send(
                embed=Embed(
                    description=f"**{a_name}** does not have enough raid participants to continue with the raid.",
                    color=COLOR
                )
            )
            clear()
            return

        embed = Embed(
            title="Defend your faction",
            description=f"**{d_name}** is being raided! Click the button below to defend!",
            color=COLOR
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(
            f"<@&{FACTIONS[d_faction]}>",
            embed=embed,
            view=RaidDefenseButton(d_faction, self.db)
        )
        await asyncio.sleep(1200)

        a_score = 0
        d_score = 0
        if len(d_members) == 0:
            await ctx.send(
                embed=Embed(
                    description=f"No Divergent of **{d_name}** was there to defend the raid!",
                    color=COLOR
                )
            )
        else:
            for user in a_members:
                a_score += await self.db.get_pow_lvl(user)
            for user in d_members:
                d_score += await self.db.get_pow_lvl(user)

        if a_score >= d_score:  # Attacker won
            for user in d_members:
                await self.db.change_relative_value(user, 0.5, "hp")
                await self.db.change_value(user, get_loser_xp(), "xp")
                await self.db.use_gear(user, "armor")

            f_coins = await self.db.get_faction_value(d_faction, "coins")
            total_reward = round(f_coins * 0.1)
            await self.db.change_faction_value(d_faction, -total_reward, "coins")
            await self.db.change_faction_value(a_faction, total_reward, "coins")

            for user in a_members:
                await self.db.change_value(user, get_winner_xp(), "xp")
                await self.db.use_gear(user, "weapon")

            embed = Embed(
                title=f"{a_name} won the raid!",
                description=f"Congratulations! **{a_name}** steals 10% of the other faction's treasury!",
                color=COLOR
            )
        else:  # Defender won
            for user in a_members:
                await self.db.change_relative_value(user, 0.5, "hp")
                await self.db.change_value(user, get_loser_xp(), "xp")
                await self.db.use_gear(user, "armor")

            f_coins = await self.db.get_faction_value(a_faction, "coins")
            total_reward = round(f_coins * 0.1)
            await self.db.change_faction_value(a_faction, -total_reward, "coins")
            await self.db.change_faction_value(d_faction, total_reward, "coins")

            for user in d_members:
                await self.db.change_value(user, get_winner_xp(), "xp")
                await self.db.use_gear(user, "weapon")

            embed = Embed(
                title=f"{d_name} won the raid!",
                description=f"Congratulations! **{d_name}** steals 10% of the other faction's treasury!",
                color=COLOR
            )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(embed=embed)
        clear()


def setup(bot):
    bot.add_cog(Combat(bot))


class AcceptRefuseButton(discord.ui.View):
    def __init__(self, attacker, defender, db):
        self.attacker = attacker
        self.defender = defender
        self.db = db
        super().__init__(timeout=None)

    async def combat(self, attacker, defender, interaction):
        await self.db.use_gear(attacker, "weapon")
        await self.db.use_gear(attacker, "armor")
        await self.db.use_gear(defender, "weapon")
        await self.db.use_gear(defender, "armor")

        battle[attacker.id] = True
        battle[defender.id] = True
        _, a_cel, _, _ = await self.db.get_combat_stats(attacker)
        _, d_cel, _, _ = await self.db.get_combat_stats(defender)

        a_hp = await self.db.get_value(attacker, "hp")
        d_hp = await self.db.get_value(defender, "hp")

        if a_cel >= d_cel:  # attacker begins
            a = True
            begin_txt = f"\n\n{attacker.mention} will attack first!"
        else:  # defender begins
            a = False
            begin_txt = f"\n\n{defender.mention} will attack first!"

        embed = interaction.message.embeds[0]

        embed.description = f"{defender.mention} accepted the duel. Get ready to fight! {begin_txt}"
        set_thumbnail(defender, embed)
        await interaction.message.edit(embed=embed)
        await asyncio.sleep(5)

        while True:
            if not battle[attacker.id] or not battle[defender.id]:  # check if someone escaped
                embed.description = f"Duel ended!"
                await interaction.message.edit(embed=embed)
                break

            a_dmg, a_cel, a_cr, a_dr = await self.db.get_combat_stats(attacker)
            d_dmg, d_cel, d_cr, d_dr = await self.db.get_combat_stats(defender)
            if a:  # attacker's turn
                a_dmg = a_dmg if random.randint(1, 100) not in range(1, round(d_dr)) else 0  # defender dodged
                a_dmg = a_dmg if random.randint(1, 100) not in range(1, round(a_dr)) else a_dmg * 3  # critical hit
                a_dmg -= await self.db.get_gear_value(defender, "armor")  # defender's armor
                d_hp -= a_dmg
                d_hp = max(1, d_hp)
                a = False
                set_thumbnail(attacker, embed)
                embed.description = f"""
                                    {attacker.mention} dealt **{a_dmg}** damage to {defender.mention}.\n
                                    {defender.mention} has **{d_hp} HP** left.
                                    """
                await interaction.message.edit(embed=embed)
            else:  # defender's turn
                d_dmg = d_dmg if random.randint(1, 100) not in range(1, round(a_dr)) else 0  # attacker dodged
                d_dmg = d_dmg if random.randint(1, 100) not in range(1, round(d_dr)) else d_dmg * 3  # critical hit
                d_dmg -= await self.db.get_gear_value(attacker, "armor")  # attacker's armor
                a_hp -= d_dmg
                a_hp = max(1, a_hp)
                a = True
                set_thumbnail(defender, embed)
                embed.description = f"""
                                    {defender.mention} dealt **{d_dmg}** damage to {attacker.mention}.\n
                                    {attacker.mention} has **{a_hp} HP** left.
                                    """
                await interaction.message.edit(embed=embed)

            await asyncio.sleep(5)
            if a_hp <= 1:  # attacker lost
                a_coins = await self.db.get_value(attacker)
                coins_lost = round(a_coins * 0.1)
                await self.db.change_value(attacker, -coins_lost)
                await self.db.change_value(defender, coins_lost)
                await self.db.change_value(defender, get_winner_xp(), "xp")
                await self.db.change_value(attacker, get_loser_xp(), "xp")

                embed.description = f"""
                    {defender.mention} won the battle with **{d_hp}** HP left.\n
                    {attacker.mention} has **{a_hp} HP** left and lost **{coins_lost}** {CURRENCY} to {defender.mention}.
                    """
                await interaction.message.edit(embed=embed)
                break
            elif d_hp <= 1:  # defender lost
                d_coins = await self.db.get_value(defender)
                coins_lost = round(d_coins * 0.1)
                await self.db.change_value(defender, -coins_lost)
                await self.db.change_value(attacker, coins_lost)
                await self.db.change_value(attacker, get_winner_xp(), "xp")
                await self.db.change_value(defender, get_loser_xp(), "xp")

                embed.description = f"""
                    {attacker.mention} won the battle with **{a_hp}** HP left.\n
                    {defender.mention} has **{d_hp} HP** left and lost **{coins_lost}** {CURRENCY} to {attacker.mention}.
                    """
                await interaction.message.edit(embed=embed)
                break

        if battle[attacker.id] and battle[defender.id]:
            await self.db.set_value(attacker, a_hp, "hp")
            await self.db.set_value(defender, d_hp, "hp")
        battle[attacker.id] = False
        battle[defender.id] = False

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def button_callback1(self, button, interaction):
        if interaction.user.id != self.defender.id:
            await interaction.response.send_message("This challenge is meant for a different user.", ephemeral=True)
            return
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.combat(self.attacker, self.defender, interaction)

    @discord.ui.button(label="Refuse", style=discord.ButtonStyle.red)
    async def button_callback2(self, button, interaction):
        if interaction.user.id != self.defender.id:
            await interaction.response.send_message("This challenge is meant for a different user.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        new_embed = interaction.message.embeds[0]
        new_embed.description = f"{self.defender.mention} declined the duel."
        await interaction.response.edit_message(embed=new_embed, view=self)


class FactionRaidButton(discord.ui.View):
    def __init__(self, faction, db):
        self.faction = faction
        self.db = db
        self.counter = 0
        super().__init__(timeout=600)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def button_callback(self, button, interaction):
        hp = await self.db.get_value(interaction.user, "hp")
        if hp <= 1:
            await interaction.response.send_message("You need more HP to join the raid.", ephemeral=True)
            return

        faction = await self.db.check_faction(interaction.user)
        if faction is None or faction != self.faction:
            await interaction.response.send_message("You are not a Divergent of this faction.", ephemeral=True)
            return
        if interaction.user not in a_members:
            a_members.append(interaction.user)
            self.counter += 1
            button.label = f"Join ({self.counter})"
            await interaction.message.edit(view=self)
        await interaction.response.send_message("You joined the raid.", ephemeral=True)


class RaidDefenseButton(discord.ui.View):
    def __init__(self, faction, db):
        self.faction = faction
        self.db = db
        self.counter = 0
        super().__init__(timeout=1200)

    @discord.ui.button(label="Join", style=discord.ButtonStyle.green)
    async def button_callback(self, button, interaction):
        hp = await self.db.get_value(interaction.user, "hp")
        if hp <= 1:
            await interaction.response.send_message("You need more HP to join the raid.", ephemeral=True)
            return

        faction = await self.db.check_faction(interaction.user)
        if faction is None or faction != self.faction:
            await interaction.response.send_message("You are not a Divergent of this faction.", ephemeral=True)
            return
        if interaction.user not in d_members:
            d_members.append(interaction.user)
            self.counter += 1
            button.label = f"Join ({self.counter})"
            await interaction.message.edit(view=self)
        await interaction.response.send_message("You joined the defense!", ephemeral=True)
