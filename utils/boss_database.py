import aiosqlite

class BossDatabase:
    async def create_boss(self, name, image_url, strength, resistance, hp, time):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                "INSERT INTO boss (name, image, str, res, hp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, strength, resistance, image_url, hp, time)
            )
            await db.commit()

    async def get_boss_id(self):
        async with aiosqlite.connect(self.DB) as db:
            cursor = await db.execute(
                "SELECT * FROM boss WHERE id = (SELECT MAX(id) FROM boss)",
            )
            boss_id = await cursor.fetchone()
            return boss_id    

    async def get_boss_info(self, boss_id):
        async with aiosqlite.connect(self.DB) as db:
            cursor = await db.execute(
                "SELECT * FROM boss WHERE id = ?",
                (boss_id,)
            )
            boss_info = await cursor.fetchone()
            return boss_info

    async def add_boss_attacker(boss_id, user_id, damage):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                "INSERT INTO boss_attackers (boss_id, user_id, damage) VALUES (?, ?, ?)",
                (boss_id, user_id, damage)
            )
            await db.commit()

    async def get_boss_attackers(boss_id):
        async with aiosqlite.connect(self.DB) as db:
            cursor = await db.execute(
                "SELECT user_id FROM boss_attackers WHERE boss_id = ?",
                (boss_id,)
            )
            attackers = await cursor.fetchall()
            return attackers

    async def give_currency(user_id, amount):
        # Placeholder function to give currency to a user
        pass

    async def reset_boss_info(boss_id):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                "DELETE FROM boss WHERE id = ?",
                (boss_id,)
            )
            await db.execute(
                "DELETE FROM boss_attackers WHERE boss_id = ?",
                (boss_id,)
            )
            await db.commit()
    async def clean_all_boss(self):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute(
                "DELETE FROM boss"
            )
            await db.execute(
                "DELETE FROM boss_attackers"
            )
            await db.commit()
    async def check_boss_exists(self):
        async with aiosqlite.connect(self.DB) as db:
            async with db.execute("SELECT COUNT(*) FROM boss") as cursor:
                result = await cursor.fetchone()
                boss_count = result[0]
                return boss_count > 0
    
    async def delete_boss_tables(self):
        async with aiosqlite.connect(self.DB) as db:
            await db.execute("DROP TABLE IF EXISTS boss")
            await db.execute("DROP TABLE IF EXISTS boss_attackers")
            await db.commit()
