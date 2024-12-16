import aiosqlite

DB_LOCATION = 'database/database.db'


async def init_db():
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY,
                                excursions_lasts INTEGER DEFAULT 1,
                                is_premium INTEGER DEFAULT 0
                            )''')
        await db.commit()

        await db.execute('''CREATE TABLE IF NOT EXISTS quests (
                                        id INTEGER PRIMARY KEY,
                                        name TEXT,
                                        description TEXT,
                                        difficulty TEXT,
                                        photo_id TEXT,
                                        location TEXT
                                    )''')
        await db.commit()


async def user_profile(tg_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        # Добавляем юзера если его нет
        await db.execute('''INSERT OR IGNORE INTO users (id) VALUES (?)''',
                         (tg_id,))
        await db.commit()

        async with db.execute("SELECT * FROM users WHERE id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return row


async def add_quest(name: str, description: str, difficulty: str, photo_id: str, location: str):
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''INSERT INTO quests (name, description, difficulty, photo_id, location) 
                            VALUES (?, ?, ?, ?, ?)''',
                         (name, description, difficulty, photo_id, location))
        await db.commit()


async def delete_quest(quest_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''DELETE FROM quests WHERE id = ?''', (quest_id,))
        await db.commit()


async def get_all_quests():
    async with aiosqlite.connect(DB_LOCATION) as db:
        async with db.execute("SELECT * FROM quests") as cursor:
            rows = await cursor.fetchall()
            return rows


async def get_quest(quest_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        async with db.execute("SELECT * FROM quests WHERE id = ?", (quest_id,)) as cursor:
            row = await cursor.fetchone()
            return row


async def process_user_quest(tg_id: int):
    # Либо делаем -1 в оставшихся запросах, либо выкидываем ошибку, что запросы закончились
    user_data = await user_profile(tg_id)
    if user_data[1] == 0 and user_data[2] == 0:
        raise Exception()
    elif user_data[2] == 0 or user_data[1] > 0:
        async with aiosqlite.connect(DB_LOCATION) as db:
            await db.execute('''UPDATE users SET excursions_lasts = excursions_lasts - 1 WHERE id = ?''',
                             (tg_id,))
            await db.commit()


async def set_premium(tg_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''UPDATE users SET is_premium = 1 WHERE id = ?''',
                         (tg_id,))
        await db.commit()
