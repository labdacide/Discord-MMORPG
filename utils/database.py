import discord
from discord.utils import utcnow

import aiosqlite
import asyncio

from config import FACTIONS

class Database:
    DB = "divergent.db"

    async def setup_db(self):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                faction TEXT,
                coins INTEGER DEFAULT 0,
                str INTEGER DEFAULT 1,
                res INTEGER DEFAULT 1,
                agi INTEGER DEFAULT 1,
                ment INTEGER DEFAULT 1,
                men INTEGER DEFAULT 1,
                lvl INTEGER DEFAULT 0,
                xp INTEGER DEFAULT 0,
                kar INTEGER DEFAULT 0,
                hp INTEGER DEFAULT 1,
                kills INTEGER DEFAULT 0,
                weapon INTEGER DEFAULT 0,
                armor INTEGER DEFAULT 0,
                wallet_code TEXT
                )"""
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS factions (
                faction TEXT PRIMARY KEY,
                coins INTEGER DEFAULT 0
                )"""
            )
            await db.execute(
                """
                ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_code TEXT
                """
            )
            for faction in FACTIONS.keys():
                await db.execute("INSERT OR IGNORE INTO factions (faction) VALUES (?)", (faction,))
            await db.commit()

    async def check_member(self, member: discord.Member):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (member.id,))
            await db.commit()

    async def check_faction(self, member: discord.Member):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute("SELECT faction FROM users WHERE user_id = ?", (member.id,)) as cursor:
                result = await cursor.fetchone()
                if result is not None:
                    return result[0]
                else:
                    return None

    async def set_faction(self, member: discord.Member, faction):
        await self.check_member(member)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET faction = ? WHERE user_id = ?", (faction, member.id,))
            await db.commit()

    async def set_value(self, member: discord.Member, amount: int, value: str = "coins"):
        await self.check_member(member)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET {value} = {amount} WHERE user_id = ?", (member.id,))
            await db.commit()

    async def restore_health(self, member: discord.Member, percent: int):
        await self.check_member(member)
        max_hp = await self.get_max_hp(member)
        amount = round(max_hp * percent / 100)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET hp = hp + {amount} WHERE user_id = ?", (member.id,))
            await db.commit()
        await self.check_max_values(member)
        new_value = await self.get_value(member, "hp")
        return new_value

    async def restore_men(self, member: discord.Member, percent: int):
        await self.check_member(member)
        max_men = await self.get_value(member, "men")
        amount = round(max_men * percent / 100)
        amount = max(amount, 1)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET ment = ment + {amount} WHERE user_id = ?", (member.id,))
            await db.commit()
        await self.check_max_values(member)
        new_value = await self.get_value(member, "ment")
        return new_value

    async def change_value(self, member: discord.Member, change: int, value: str = "coins", enable_tax: bool = True):
        await self.check_member(member)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET {value} = {value} + {round(change)} WHERE user_id = ?", (member.id,))
            await db.commit()

        if value == "hp" or value == "ment" or value == "kar":
            await self.check_max_values(member)
        elif value == "coins" and enable_tax:
            await self.add_tax(await self.check_faction(member), change)
        elif value == "kills":
            kill_count = await self.get_value(member, "kills")
            if kill_count % 10 == 0:
                await self.change_value(member, 1, "kar")

    async def check_max_values(self, member):
        max_hp = await self.get_max_hp(member)
        hp = await self.get_value(member, "hp")

        if hp > max_hp:
            await self.set_value(member, max_hp, "hp")

        async with aiosqlite.connect(self.DB) as db:  # that does not work for Max HP because max_hp ist not in DB
            await db.execute(f"UPDATE users SET ment = men WHERE ment > men")
            await db.execute(f"UPDATE users SET hp = 0 WHERE hp <= 0")
            await db.execute(f"UPDATE users SET kar = 0 WHERE kar <= 0")
            await db.commit()

    async def add_tax(self, faction, amount):
        if faction is None:
            return
        tax = abs(round(amount * 0.1))  # 10 % tax
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE factions SET coins = coins + {tax} WHERE faction = ?", (faction,))
            await db.commit()

    async def change_relative_value(self, member: discord.Member, change, value: str):
        await self.check_member(member)
        start_value = await self.get_value(member, value)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE users SET {value} = ROUND({value} * {change}) WHERE user_id = ?", (member.id,))
            await db.commit()

        end_value = await self.get_value(member, value)
        return end_value - start_value

    async def get_value(self, member: discord.Member, value: str = "coins"):
        await self.check_member(member)
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"SELECT {value} FROM users WHERE user_id = ?", (member.id,)) as cursor:
                value = (await cursor.fetchone())[0]
        return value

    async def get_faction_value(self, faction: str, value: str = "coins"):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"SELECT {value} FROM factions WHERE faction = ?", (faction,)) as cursor:
                value = (await cursor.fetchone())[0]
        return value

    async def change_faction_value(self, faction: str, change: int, value: str = "coins"):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE factions SET {value} = {value} + {change} WHERE faction = ?", (faction,))
            await db.commit()

    # Method registers a wallet and stores wallet_code for the member
    async def get_wallet_code(self, member: discord.Member):
        code = await self.get_value(member, "wallet_code")      
        if (!code) :
            res = await requests.post(os.getenv("WEBHOOK_WALLET_ONBOARDING"))
            data = res.json()
            self.set_value(member, code, "wallet_code")
            return data.code
        return code

    async def get_max_hp(self, member: discord.Member):
        res = await self.get_value(member, "res")
        return 25 + 5 * res

    async def get_base_stats(self, member):
        await self.check_member(member)
        _str = await self.get_value(member, "str")
        res = await self.get_value(member, "res")
        agi = await self.get_value(member, "agi")
        men = await self.get_value(member, "men")
        ment = await self.get_value(member, "ment")

        return _str, res, agi, men, ment

    async def get_combat_stats(self, member):
        _str, res, agi, men, ment = await self.get_base_stats(member)
        kar = await self.get_value(member, "kar")

        weapon = await self.get_gear_value(member, "weapon")
        dmg = 2 + weapon + _str + 0.5*agi + 0.25*ment
        cel = (4*agi + 2*men)
        cr = 2.5 + (0.2*agi + 0.2*men) - 0.1*kar
        dr = 5 + 0.1*cel - 0.1*kar

        return round(dmg), cel, cr, dr

    async def get_pow_lvl(self, member):
        dmg, cel, cr, dr = await self.get_combat_stats(member)
        men = await self.get_value(member, "men")
        hp = await self.get_value(member, "hp")
        pow_lvl = 10 * hp + 2 * dmg + 100 * cr + 100 * dr + cel + men

        return round(pow_lvl)

    @staticmethod
    def get_power_level_sql():
        cel = "(4*agi + 2*men)"

        #                     ----------------- dmg -----------------   ------------------- cr ------------------
        return f"ROUND(10*hp + 2*(2 + str + 0.5*agi + 0.25*ment) + 100*(2.5 + 0.2*agi + 0.2*men - 0.1*kar) " \
               f"+ 100*(5 + 0.1*{cel} - 0.1*kar) + {cel} + men)"
        #          ------------ dr ------------

    async def get_sec_stats(self, member):
        lvl = await self.get_value(member, "lvl")
        xp = await self.get_value(member, "xp")
        kar = await self.get_value(member, "kar")
        kills = await self.get_value(member, "kills")

        return lvl, xp, kar, kills

    async def wait_for_revive(self, member) -> bool:
        """Returns False if the member was not revived"""
        counter = 0
        while True:
            if counter >= 300:
                return False

            hp = await self.get_value(member, "hp")
            if hp <= 0:
                counter += 1
                await asyncio.sleep(1)
            else:
                return True

    async def loot_dead_member(self, dead_member, killer):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(f"UPDATE has_item SET user_id = ? WHERE user_id = ?", (killer.id, dead_member.id))
            await db.commit()

    async def death(self, dead_member, killer, channel):
        revive = await self.wait_for_revive(dead_member)
        if revive:
            await self.set_value(dead_member, 5, "hp")
        else:
            embed = discord.Embed(
                title="Death",
                description=f"{dead_member.mention} was not revived and died.",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url=dead_member.display_avatar.url)

            # double check if member is really dead
            hp = await self.get_value(dead_member, "hp")
            if hp > 0:
                print(f"[{utcnow()}] Death Error for {dead_member} (Killer: {killer}): Member has {hp} HP")
                return

            try:
                await channel.send(f"{dead_member.mention}", embed=embed)
            except Exception as e:
                print(f"[{utcnow()}] Death Message Error for {dead_member} (Killer: {killer}): {e}")
                return

            print(f"[{utcnow()}] Death: {dead_member} in channel #{channel.name} ({channel.id}), killed by {killer} ")
            await self.loot_dead_member(dead_member, killer)
            await self.reset_stats(dead_member)

    async def reset_stats(self, member):
        await self.set_value(member, 1, "str")
        await self.set_value(member, 1, "res")
        await self.set_value(member, 1, "agi")
        await self.set_value(member, 1, "men")
        await self.set_value(member, 1, "ment")
        await self.set_value(member, 0, "lvl")
        await self.set_value(member, 0, "xp")
        await self.set_value(member, 1, "hp")
        await self.set_value(member, 0, "kills")
        await self.set_value(member, 0, "kar")

    async def get_possible_lvl(self, member):
        xp = await self.get_value(member, "xp")

        count = 50
        if xp <= 50:
            return 1
        else:
            for number in range(1, 100):
                count += round(count * 0.5)
                if count >= xp:
                    return number
            return 100

    async def lvl_up_available(self, member) -> bool:
        possible_lvl = await self.get_possible_lvl(member)
        lvl = await self.get_value(member, "lvl")
        if possible_lvl > lvl:
            return True
        else:
            return False

    async def get_gear_id(self, member, gear_type):
        """Returns the ID of the gear item the user has equipped."""
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""SELECT items.id FROM users, items 
                    WHERE user_id = ? AND users.{gear_type} = items.id""", (member.id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result is None:
                    return None
        return result[0]

    async def get_gear_value(self, member, gear_type: str):
        gear_id = await self.get_gear_id(member, gear_type)
        if gear_id is None:
            return 0
        active = await self.check_item(member, "damage", gear_id)
        if not active:
            return 0
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"""SELECT effect_value FROM users, items 
            WHERE user_id = ? AND users.{gear_type} = items.id""", (member.id,)) as cursor:
                result = await cursor.fetchone()
                if result is None:
                    return 0

        return result[0]

    async def get_gear_uses(self, member, gear_name) -> str:
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"""SELECT uses_left FROM has_item, items
            WHERE item_id = (SELECT id FROM items WHERE name = ?) AND (effect = 'damage' OR effect = 'defense')
            AND user_id = ? AND items.id = item_id""", (gear_name, member.id)) as cursor:
                result = await cursor.fetchone()
                if result is None or result[0] is None:
                    async with db.execute(
                            f"""SELECT duration, effect FROM items WHERE name = ?""", (gear_name,)
                    ) as cursor2:
                        duration, effect = await cursor2.fetchone()
                        if effect != "damage" and effect != "defense":
                            return ""
                        return f"({duration} uses left)"
                else:
                    return f"({result[0]} uses left)"

    async def get_item_uses(self, member, own_id) -> int:
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"""SELECT uses_left FROM has_item, items
            WHERE has_item.id = ?
            AND user_id = ? AND items.id = item_id""", (own_id, member.id)) as cursor:
                result = await cursor.fetchone()
                if result is None:
                    return 0
                else:
                    return result[0]

    async def get_gear_type(self, gear_name: str):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(f"""SELECT type FROM items WHERE name = ?""", (gear_name,)) as cursor:
                result = await cursor.fetchone()
                if result is None:
                    return None

        return result[0]

    async def get_item_image(self, item):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute("SELECT image FROM items WHERE name = ?", (item,)) as cursor:
                result = await cursor.fetchone()
                if result is None:
                    return None

        return result[0]

    async def use_item(self, member, effect):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                    """
                    UPDATE has_item
                    SET uses_left = uses_left - 1
                    WHERE is_active = 1 AND user_id = ? 
                    AND item_id IN (SELECT id FROM items WHERE effect = ?)
                    """, (member.id, effect)
            )
            await db.commit()

    async def use_gear(self, member, gear_type):
        gear_id = await self.get_gear_id(member, gear_type)
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                """
                UPDATE has_item
                SET uses_left = uses_left - 1
                WHERE is_active = 1 AND user_id = ?
                AND item_id = ?
                """, (member.id, gear_id)
            )
            await db.commit()

    async def check_item(self, member, effect, item_id=None) -> bool:
        """Check if member has the specified item activated."""
        if item_id is None:
            id_str = ""
        else:
            id_str = f"OR item_id = {item_id}"

        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""
                    SELECT * FROM has_item, items 
                    WHERE items.id = has_item.item_id AND is_active = 1 AND user_id = ? 
                    AND (items.effect = ? {id_str})
                    AND (uses_left > 0 OR datetime(end) > datetime('now'))
                    """, (member.id, effect)
            ) as cursor:
                row_count = len(await cursor.fetchall())

        if row_count == 0:
            return False
        return True

    async def remove_old_items(self):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute(
                    f"""
                    SELECT has_item.id FROM has_item, items 
                    WHERE items.id = has_item.item_id AND is_active = 1
                    AND (uses_left <= 0 AND datetime(end) <= datetime('now'))
                    """,
            ) as cursor:
                async for has_item_id in cursor:
                    await db.execute("DELETE FROM has_item WHERE id = ?", (has_item_id[0],))
                await db.commit()
