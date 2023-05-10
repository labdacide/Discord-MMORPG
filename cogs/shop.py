import discord
from discord import Embed
from discord.utils import basic_autocomplete
from discord.ext import commands
from discord.commands import slash_command, Option
from collections import Counter

from config import *
from utils import *

import aiosqlite
from sqlite3 import PARSE_DECLTYPES
from datetime import datetime, timedelta

SHOP_DB = Database.DB


async def autocomplete_items(ctx: discord.ApplicationContext):
    items = []
    async with aiosqlite.connect(SHOP_DB) as db:
        async with db.execute("SELECT name, effect FROM items") as cursor:
            async for name in cursor:
                items.append(name[0])
    return items


async def autocomplete_all_owned_items(ctx: discord.AutocompleteContext):
    items = []
    async with aiosqlite.connect(SHOP_DB) as db:
        async with db.execute("""SELECT name FROM has_item, items WHERE user_id = ?
        AND items.id = has_item.item_id AND (uses_left > 0 or uses_left IS NULL)""",
                              (ctx.interaction.user.id,)) as cursor:
            async for name in cursor:
                items.append(name[0])
    return list(Counter(items).keys())


async def autocomplete_owned_items(ctx: discord.AutocompleteContext):
    items = []
    async with aiosqlite.connect(SHOP_DB) as db:
        async with db.execute("""SELECT name, effect FROM has_item, items WHERE user_id = ?
        AND items.id = has_item.item_id AND (uses_left > 0 OR uses_left IS NULL)""",
                              (ctx.interaction.user.id,)) as cursor:
            async for name, effect in cursor:
                if effect not in gear_effects:
                    items.append(name)
    return list(Counter(items).keys())


async def autocomplete_owned_gear(ctx: discord.AutocompleteContext):
    items = []
    async with aiosqlite.connect(SHOP_DB) as db:
        async with db.execute("""SELECT name FROM has_item, items WHERE user_id = ?
        AND items.id = has_item.item_id AND (uses_left > 0 OR uses_left IS NULL)
        AND (type = 'armor' OR type = 'weapon')""", (ctx.interaction.user.id,)) as cursor:
            async for item in cursor:
                items.append(item[0])
    return list(Counter(items).keys())


class Shop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.Cog.listener()
    async def on_ready(self):
        await Shop.setup_db()

    @staticmethod
    async def setup_db():
        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                name TEXT,
                image TEXT,
                price INTEGER DEFAULT 0,
                type TEXT DEFAULT 'powerup',
                effect TEXT,
                effect_value INTEGER DEFAULT 0,
                duration INTEGER DEFAULT 0,
                unit TEXT
                )"""
            )

            await db.execute(
                """CREATE TABLE IF NOT EXISTS has_item (  
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                item_id INTEGER,
                is_active INTEGER DEFAULT 0,
                end TIMESTAMP,
                uses_left INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (item_id) REFERENCES items(id)
                )"""
            )

            await db.commit()

    @staticmethod
    async def get_items():
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute("SELECT name FROM items") as cursor:
                async for name in cursor:
                    items.append(name[0])
        return items

    @staticmethod
    async def get_owned_items(member):
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute("""SELECT name, effect FROM has_item, items WHERE user_id = ?
            AND items.id = has_item.item_id AND (uses_left > 0 OR uses_left IS NULL)""", (member.id,)) as cursor:
                async for name, effect in cursor:
                    if effect not in gear_effects:
                        items.append(name)
        return items

    @staticmethod
    async def get_all_owned_items(member):
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute(
                    """SELECT name, duration FROM has_item, items WHERE user_id = ?
                    AND items.id = has_item.item_id AND (uses_left > 0 or uses_left IS NULL)""",
                    (member.id,)) as cursor:
                async for name, duration in cursor:
                    items.append(name)
        return items

    @staticmethod
    async def get_owned_gear(member):
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute("""SELECT name FROM has_item, items WHERE user_id = ?
            AND items.id = has_item.item_id AND (uses_left > 0 OR uses_left IS NULL)
            AND (type = 'armor' OR type = 'weapon')""", (member.id,)) as cursor:
                async for item in cursor:
                    items.append(item[0])
        return items

    async def get_inventory_string(self, member) -> str:
        owned_items = await Shop.get_all_owned_items(member)
        x = Counter(owned_items)

        item_str = ""
        for item in x.keys():
            uses_str = await self.db.get_gear_uses(member, item)
            if x[item] == 1:
                item_str += f"{item} {uses_str}\n"
            else:
                item_str += f"{item} ({x[item]}x) {uses_str}\n"

        if item_str == "":
            item_str = "You don't have any items."

        return item_str

    @slash_command(description="List of all items you can buy")
    async def shop(
            self, ctx,
            category: Option(str, "Choose a category", choices=["powerup", "armor", "weapon", "special"])
    ):
        embed = Embed(title="Shop",
                      description=f"Welcome to the {category} shop!",
                      color=COLOR)

        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute(
                    "SELECT name, price, duration, unit, effect, effect_value, type FROM items"
            ) as cursor:
                async for name, price, duration, unit, effect, value, _type in cursor:
                    if _type != category:
                        continue

                    revive_str = ""
                    if effect == "revive":
                        revive_str = "\nYou can revive yourself with this item."
                    effect_str = get_effect(effect)

                    if effect in special_effects.keys():
                        desc = f"{special_effects[effect]}"
                    elif duration == 0:
                        desc = f"Gives you {value:,} {effect_str}. {revive_str}"
                    else:
                        desc = f"Gives you {value:,} {effect_str} ({duration} {unit}). {revive_str}"

                    embed.add_field(
                        name=f"**{name}** - 🪙 {price:,} ",
                        value=f"{desc}",
                        inline=False
                    )

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.respond(embed=embed)

    @slash_command(description="Buy a new item")
    async def buy(self, ctx, item: Option(str, "The item you want to buy",
                                          autocomplete=basic_autocomplete(autocomplete_items))):
        if item not in await self.get_items():
            await ctx.respond("That item does not exist", ephemeral=True)
            return

        points = await self.db.get_value(ctx.author)
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute("SELECT price, id, image FROM items WHERE name = ?", (item,)) as cursor:
                cost, item_id, image_url = await cursor.fetchone()

        if cost > points:
            missing = cost - points
            await ctx.respond(embed=Embed(
                title="Purchase failed",
                description=f"You don't have enough {CURRENCY} to buy `{item}`.\n\n"
                            f"You need **{missing:,}** more {CURRENCY}.",
                color=COLOR), ephemeral=True)
            return

        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute("PRAGMA foreign_keys = 1")
            await db.execute("INSERT INTO has_item (user_id, item_id) VALUES (?, ?)", (ctx.author.id, item_id))
            await db.commit()

        await self.db.change_value(ctx.author, 0 - cost)
        # new_balance = await self.db.get_value(ctx.author)
        embed = Embed(title="Success",
                      description=f"You bought `{item}` for **{cost:,}** {CURRENCY}!",
                      color=COLOR)
        embed.set_thumbnail(url=image_url)
        await try_embed(ctx, embed)

    @slash_command(description="Use one of your items")
    async def use(
            self, ctx,
            item: Option(
                str, "The item you want to use",
                autocomplete=basic_autocomplete(autocomplete_owned_items)  # no gear
            )
    ):
        if item not in await self.get_owned_items(ctx.author):
            await ctx.respond("You don't own this item", ephemeral=True)
            return

        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute(
                    """
                    SELECT has_item.id, image, effect, effect_value, duration, unit, has_item.user_id, is_active
                    FROM has_item, items
                    WHERE user_id = ? and item_id = (SELECT id FROM items WHERE name = ?) 
                    AND (uses_left > 0 OR uses_left IS NULL)
                    AND has_item.item_id = items.id""", (ctx.author.id, item)) as cursor:
                item_own_id, image_url, effect, effect_value, duration, unit, user_id, is_active = await cursor.fetchone()

        user_hp = await self.db.get_value(ctx.author, "hp")
        if effect == "hp" and user_hp <= 0:
            await ctx.respond("You can't use this item while you are dead", ephemeral=True)
            return
        if effect == "revive":
            effect = "hp"

        uses_left = 0
        if unit == "hours":
            expire_time = datetime.utcnow() + timedelta(hours=duration)
        elif unit == "minutes":
            expire_time = datetime.utcnow() + timedelta(minutes=duration)
        else:
            expire_time = datetime.utcnow()
            uses_left = duration

        if is_active == 0:
            async with aiosqlite.connect(SHOP_DB, detect_types=PARSE_DECLTYPES) as db:
                await db.execute(
                    """UPDATE has_item SET is_active = 1, end = ?, uses_left = ? WHERE id = ?""",
                    (expire_time, uses_left, item_own_id))
                await db.commit()

        # add effect to user
        if effect not in special_effects.keys():
            await self.db.change_value(ctx.author, effect_value, effect)
            async with aiosqlite.connect(SHOP_DB) as db:
                await db.execute(f"""UPDATE has_item SET uses_left = uses_left - 1 WHERE id = ?""", (item_own_id,))
                await db.commit()
            duration = await self.db.get_item_uses(ctx.author, item_own_id)

        desc = f"The effect will expire in **{duration}** {unit}."
        if unit == "uses":
            if duration <= 0:
                duration = "no"
            desc = f"This item has {duration} uses left."

        embed = Embed(
            title="Success",
            description=f"You used **{item}**!\n\n{desc}",
            color=COLOR
        )
        embed.set_thumbnail(url=image_url)
        await try_embed(ctx, embed)
        await self.db.remove_old_items()

    @slash_command(description="Show your inventory")
    async def inventory(
            self, ctx,
            member: Option(discord.Member, "Choose a divergent", required=False, default=None)
    ):
        if member is None:
            member = ctx.author
        elif not ctx.author.guild_permissions.administrator:
            await ctx.respond("You don't have permission to see this.", ephemeral=True)
            return

        coins = await self.db.get_value(member)
        item_str = await self.get_inventory_string(member)

        embed = Embed(title="Inventory",
                      description=f"{member.mention} has **{coins:,}** {CURRENCY}.",
                      color=COLOR)
        embed.add_field(name="Items", value=item_str, inline=False)
        set_thumbnail(member, embed)
        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="Give an item to a Divergent")
    async def giveitem(
            self, ctx,
            member: Option(discord.Member, "Choose a Divergent"),
            item: Option(str, "Choose an Item", autocomplete=basic_autocomplete(autocomplete_all_owned_items)),
            amount: Option(int, "The amount of items", min_value=1, default=1, required=False)
    ):
        items = []
        async with aiosqlite.connect(SHOP_DB) as db:
            async with db.execute(
                    "SELECT id FROM has_item WHERE item_id = (SELECT id FROM items WHERE name = ?) AND user_id = ?",
                    (item, ctx.author.id)) as cursor:
                async for _id in cursor:
                    items.append(_id[0])

        if amount > len(items):
            await ctx.respond(f"You only have {len(items)}x {item}.", ephemeral=True)
            return

        for _id in items[:amount]:
            async with aiosqlite.connect(SHOP_DB) as db:
                await db.execute("""UPDATE has_item SET user_id = ? WHERE id = ?""", (member.id, _id,))
                await db.commit()

        embed = Embed(
            title="Items sent!",
            description=f"You gave {amount}x **{item}** to {member.mention}",
            color=COLOR
        )
        image_url = await self.db.get_item_image(item)
        embed.set_thumbnail(url=image_url)
        await try_embed(ctx, embed)

    @slash_command(description="Give krykoins to another user")
    async def givekrykoins(
            self, ctx,
            member: Option(discord.Member, "Specify a Divergent"),
            amount: Option(int, "The amount of krykoins", min_value=1)
    ):
        if ctx.author.id == member.id:
            await ctx.respond("You can't give yourself krykoins.", ephemeral=True)
            return

        coins = await self.db.get_value(ctx.author)
        if coins < amount:
            await ctx.respond(f"You only have **{coins:,}** {CURRENCY}", ephemeral=True)
            return

        await self.db.change_value(ctx.author, -amount, enable_tax=False)
        await self.db.change_value(member, amount, enable_tax=False)

        embed = Embed(
            title="Krykoins sent",
            description=f"You sent **{amount:,}** {CURRENCY} to {member.mention}.",
            color=COLOR
        )
        set_thumbnail(ctx.author, embed)
        await ctx.respond(f"{member.mention}", embed=embed)

    @slash_command(description="Equip your gear")
    async def equip(
            self, ctx,
            gear: Option(str, "The gear you want to use", autocomplete=basic_autocomplete(autocomplete_owned_gear))
    ):
        if gear not in await self.get_owned_gear(ctx.author):
            await ctx.respond("You don't own this gear", ephemeral=True)
            return

        gear_type = await self.db.get_gear_type(gear)
        if gear_type is None:
            await ctx.respond("This item does not exist", ephemeral=True)
            return

        gear_id = await self.db.get_gear_id(ctx.author, gear_type)

        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute(f"""UPDATE users SET {gear_type} = (SELECT id FROM items WHERE name = ?) 
                             WHERE user_id = ?""", (gear, ctx.author.id))
            await db.execute(
                """UPDATE has_item SET is_active = 1, end = ?, uses_left = (SELECT duration FROM items WHERE id = ?)
                WHERE item_id = ? AND user_id = ?""",
                (datetime.utcnow(), gear_id, gear_id, ctx.author.id))
            await db.commit()

        await ctx.respond(f"You equipped **{gear}**")

    @slash_command(description="Add an item to the shop")
    @commands.has_permissions(administrator=True)
    async def additem(
            self, ctx,
            name: Option(str, "Name of the item"),
            image: Option(discord.Attachment, "The item picture"),
            price: Option(int, "Price in krykoins"),
            effect: Option(
                str, "The effect of the item",
                choices=["str", "res", "agi", "ment", "hp", "xp", "kar", "revive"]
            ),
            effect_value: Option(int, "How much of the effect this item will grant"),
            uses: Option(int, "How many times the item can be used", min_value=1, required=False, default=1)
    ):
        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute(
                """INSERT INTO items(name, image, price, effect, effect_value, duration, unit)
                VALUES (?,?,?,?,?,?,?)""",
                (name, image.url, price, effect, effect_value, uses, "uses"))
            await db.commit()

        await ctx.respond(f"Item **{name}** added successfully!")

    @slash_command(description="Add gear the shop")
    @commands.has_permissions(administrator=True)
    async def addgear(
            self, ctx,
            name: Option(str, "Name of the item"),
            image: Option(discord.Attachment, "Item picture"),
            gear_type: Option(str, "Type of the gear", choices=["armor", "weapon"]),
            price: Option(int, "Set a price"),
            effect_value: Option(int, "Damage or defense"),
            uses: Option(int, "How many times the gear can be used", min_value=1),
    ):
        if gear_type == "armor":
            effect = "defense"
        else:
            effect = "damage"

        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute(
                """INSERT INTO items(name, image, price, type, effect, effect_value, duration, unit)
                VALUES (?,?,?,?,?,?,?,?)""",
                (name, image.url, price, gear_type, effect, effect_value, uses, "uses"))
            await db.commit()

        await ctx.respond(f"Gear **{name}** added successfully!")

    @slash_command(description="Add a special item to the shop")
    @commands.has_permissions(administrator=True)
    async def addspecialitem(
            self, ctx,
            name: Option(str, "Name of the item"),
            image: Option(discord.Attachment, "Item picture"),
            effect_type: Option(str, "Type of the gear", choices=["trap", "shield", "stats"]),
            price: Option(int, "Set a price")
    ):
        duration_unit = "uses"
        if effect_type == "stats":
            duration = 1
        elif effect_type == "trap":
            duration = 1
        else:
            duration = 24
            duration_unit = "hours"

        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute(
                """INSERT INTO items(name, image, price, type, effect, duration, unit)
                VALUES (?,?,?,?,?,?,?)""",
                (name, image.url, price, "special", effect_type, duration, duration_unit))
            await db.commit()

        await ctx.respond(f"Special item **{name}** added successfully!")

    @slash_command(description=f"Remove an item from the shop")
    @commands.has_permissions(administrator=True)
    async def removeitem(self, ctx,
                         item: Option(str, "The item you want to remove",
                                      autocomplete=basic_autocomplete(autocomplete_items))):
        async with aiosqlite.connect(SHOP_DB) as db:
            await db.execute("DELETE FROM items WHERE name = ?", (item,))
            await db.commit()

        await ctx.respond(f"Item **{item}** deleted successfully!", ephemeral=True)
        


def setup(bot):
    bot.add_cog(Shop(bot))
    
    
    
     